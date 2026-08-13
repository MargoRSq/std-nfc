#!/bin/sh
# Базовая защита сервера по ТЗ заказчика: SSH, файрвол, бан сканеров/перебора,
# заголовки и лимиты на Caddy. Идемпотентно, вызывается из install.sh и update.sh.
#
#   sudo ./setup-security.sh            # применить (порт 22 остаётся открытым)
#   sudo ./setup-security.sh --drop-22  # закрыть 22 — ТОЛЬКО после проверки нового порта
#
# Порядок безопасный: новый SSH-порт добавляется рядом со старым, root-логин
# отключается только если есть другой пользователь с sudo и ключом.
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
[ "$(id -u)" -eq 0 ] || { echo "ERROR: запускать от root" >&2; exit 1; }
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки" >&2; exit 1; }

DROP_22=no
[ "${1:-}" = "--drop-22" ] && DROP_22=yes

getenv() { grep "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- ; }

# Стенды живут на общих хостах: смена порта SSH и ufw там отрежут доступ
# ко всему остальному, что крутится на машине.
if [ "$(getenv SECURITY_SETUP)" = "off" ]; then
    echo "  SECURITY_SETUP=off в .env — настройку защиты пропускаю (стенд)"
    exit 0
fi

SSH_PORT=$(getenv SSH_PORT); SSH_PORT=${SSH_PORT:-54368}
BANTIME=$(getenv FAIL2BAN_BANTIME); BANTIME=${BANTIME:-1h}
FINDTIME=$(getenv FAIL2BAN_FINDTIME); FINDTIME=${FINDTIME:-10m}
MAXRETRY=$(getenv FAIL2BAN_MAXRETRY); MAXRETRY=${MAXRETRY:-5}
DOMAIN=$(getenv DOMAIN)

case "$SSH_PORT" in
    ''|*[!0-9]*) echo "ERROR: SSH_PORT='$SSH_PORT' — нужно число" >&2; exit 1 ;;
esac
[ "$SSH_PORT" -ge 1024 ] && [ "$SSH_PORT" -le 65535 ] || {
    echo "ERROR: SSH_PORT должен быть в диапазоне 1024-65535" >&2; exit 1; }

echo "==> 1/6 Пакеты (ufw, fail2ban)"
export DEBIAN_FRONTEND=noninteractive
MISSING=""
command -v ufw >/dev/null 2>&1 || MISSING="$MISSING ufw"
command -v fail2ban-client >/dev/null 2>&1 || MISSING="$MISSING fail2ban"
if [ -n "$MISSING" ]; then
    apt-get update -qq
    # shellcheck disable=SC2086
    apt-get install -y -qq $MISSING
else
    echo "  уже установлены"
fi

echo "==> 2/6 SSH: порт $SSH_PORT, root-логин, лимит попыток"
# Есть ли не-root пользователь с sudo и ключом? Без него PermitRootLogin no
# оставит сервер без доступа — на проде заказчика физического доступа нет.
SUDO_USER_OK=no
for home in /home/*; do
    [ -d "$home" ] || continue
    u=$(basename "$home")
    [ -s "$home/.ssh/authorized_keys" ] || continue
    if id -nG "$u" 2>/dev/null | tr ' ' '\n' | grep -qx -e sudo -e admin -e wheel; then
        SUDO_USER_OK=yes
        echo "  sudo-пользователь с ключом: $u"
        break
    fi
done

SSHD_DROPIN=/etc/ssh/sshd_config.d/99-std-cards.conf
mkdir -p /etc/ssh/sshd_config.d
{
    echo "# std-cards: сгенерировано setup-security.sh, правки перезатрутся"
    echo "Port $SSH_PORT"
    if [ "$DROP_22" = no ]; then
        echo "# 22 остаётся до проверки нового порта: sudo ./setup-security.sh --drop-22"
        echo "Port 22"
    fi
    if [ "$SUDO_USER_OK" = yes ]; then
        echo "PermitRootLogin no"
    else
        echo "# PermitRootLogin не трогаем: не найден не-root пользователь с sudo и ssh-ключом"
    fi
    echo "MaxAuthTries 3"
    echo "LoginGraceTime 20"
    echo "X11Forwarding no"
} > "$SSHD_DROPIN.new"

# Кладём и сразу проверяем весь конфиг: битый drop-in снесёт доступ на reload.
[ -f "$SSHD_DROPIN" ] && cp "$SSHD_DROPIN" "$SSHD_DROPIN.bak"
mv "$SSHD_DROPIN.new" "$SSHD_DROPIN"
chmod 644 "$SSHD_DROPIN"
if ! sshd -t; then
    if [ -f "$SSHD_DROPIN.bak" ]; then mv "$SSHD_DROPIN.bak" "$SSHD_DROPIN"; else rm -f "$SSHD_DROPIN"; fi
    echo "ERROR: конфиг sshd не проходит проверку, изменения откачены" >&2
    exit 1
fi
rm -f "$SSHD_DROPIN.bak"

# Ubuntu 22.10+ поднимает ssh через сокет-активацию, и тогда порт задаёт
# ssh.socket, а `Port` в sshd_config молча игнорируется.
if systemctl is-active --quiet ssh.socket 2>/dev/null; then
    mkdir -p /etc/systemd/system/ssh.socket.d
    {
        echo "# std-cards: сгенерировано setup-security.sh"
        echo "[Socket]"
        echo "ListenStream="
        echo "ListenStream=$SSH_PORT"
        [ "$DROP_22" = no ] && echo "ListenStream=22"
    } > /etc/systemd/system/ssh.socket.d/99-std-cards.conf
    systemctl daemon-reload
    systemctl restart ssh.socket
    echo "  порт задан через ssh.socket (сокет-активация)"
else
    systemctl reload ssh 2>/dev/null || systemctl reload sshd
fi
[ "$SUDO_USER_OK" = yes ] || echo "  WARN: root-логин НЕ отключён — сначала заведите пользователя с sudo и ssh-ключом"
[ "$DROP_22" = yes ] && echo "  порт 22 закрыт" || echo "  слушает $SSH_PORT и 22 (22 закрыть: --drop-22)"

echo "==> 3/6 Файрвол (ufw)"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow "$SSH_PORT"/tcp comment 'ssh' >/dev/null
[ "$DROP_22" = no ] && ufw allow 22/tcp comment 'ssh legacy' >/dev/null
ufw allow 80/tcp comment 'http' >/dev/null
ufw allow 443/tcp comment 'https' >/dev/null
ufw --force enable >/dev/null
echo "  открыты: $SSH_PORT, 80, 443$([ "$DROP_22" = no ] && echo ', 22')"

# Docker публикует порты мимо ufw (цепочка DOCKER-USER). Внутренние сервисы
# (postgres/nats/minio) в compose без ports:, но если кто-то добавит — предупредим.
PUBLISHED=$(docker compose ps --format '{{.Publishers}}' 2>/dev/null \
    | tr ',' '\n' | grep -o '0\.0\.0\.0:[0-9]*' | cut -d: -f2 | sort -u \
    | grep -v -e '^80$' -e '^443$' || true)
[ -n "$PUBLISHED" ] && echo "  WARN: наружу опубликованы лишние порты: $(echo "$PUBLISHED" | tr '\n' ' ')"

echo "==> 4/6 Caddy: заголовки, лимиты, блок сканеров"
mkdir -p logs/caddy
if ! grep -q 'std-cards security' Caddyfile 2>/dev/null; then
    echo "  WARN: Caddyfile без секции безопасности — обновите бандл (git pull)"
fi

echo "==> 5/6 fail2ban"
cat > /etc/fail2ban/filter.d/caddy-auth.conf <<'EOF'
# Неудачные логины в админку std-cards (JSON access log Caddy)
[Definition]
failregex = ^.*"client_ip":"<HOST>".*"uri":"/api/auth/login".*"status":(401|403).*$
ignoreregex =
EOF

cat > /etc/fail2ban/filter.d/caddy-scan.conf <<'EOF'
# Сканирование ботом: 404/403 по чужим путям
[Definition]
failregex = ^.*"client_ip":"<HOST>".*"status":(404|403|444).*$
ignoreregex = ^.*"uri":"/(api|c|assets)/.*$
EOF

CADDY_LOG="$DIR/logs/caddy/access.log"
cat > /etc/fail2ban/jail.d/std-cards.local <<EOF
[DEFAULT]
bantime  = $BANTIME
findtime = $FINDTIME
maxretry = $MAXRETRY
backend  = auto

[sshd]
enabled  = true
port     = $SSH_PORT,22
maxretry = 3

[caddy-auth]
enabled  = true
filter   = caddy-auth
logpath  = $CADDY_LOG
port     = http,https
maxretry = 5

[caddy-scan]
enabled  = true
filter   = caddy-scan
logpath  = $CADDY_LOG
port     = http,https
maxretry = 15
findtime = 5m

[recidive]
enabled  = true
bantime  = 1w
findtime = 1d
maxretry = 3
EOF

touch "$CADDY_LOG"
systemctl enable fail2ban >/dev/null 2>&1 || true
systemctl restart fail2ban
sleep 2
JAILS=$(fail2ban-client status 2>/dev/null | sed -n 's/.*Jail list:\s*//p')
echo "  джейлы: ${JAILS:-не запустились, см. journalctl -u fail2ban}"

echo "==> 6/6 Перезапуск Caddy с новой конфигурацией"
if docker compose ps --services 2>/dev/null | grep -qx caddy; then
    docker compose up -d caddy >/dev/null 2>&1 && echo "  caddy перезапущен" \
        || echo "  WARN: caddy не перезапустился — docker compose logs caddy"
else
    echo "  caddy не запущен — пропускаю"
fi

echo ""
echo "Готово. Проверка: sudo ./verify-security.sh"
[ "$DROP_22" = no ] && cat <<EOF

ВАЖНО: не закрывая текущую SSH-сессию, откройте вторую и проверьте вход:
    ssh -p $SSH_PORT <user>@${DOMAIN:-<ip>}
Получилось — закройте старый порт: sudo ./setup-security.sh --drop-22
EOF
exit 0
