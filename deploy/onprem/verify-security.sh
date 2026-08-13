#!/bin/sh
# Проверка пунктов ТЗ по безопасности. Читает состояние системы, ничего не меняет.
# Запуск из каталога установки: sudo ./verify-security.sh
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
PASS=0; WARN=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  [ OK ] %s\n' "$1"; }
warn() { WARN=$((WARN+1)); printf '  [WARN] %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf '  [FAIL] %s\n' "$1"; }

[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки"; exit 1; }
getenv() { grep "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- ; }

if [ "$(getenv SECURITY_SETUP)" = "off" ]; then
    echo "SECURITY_SETUP=off в .env — это стенд, защита сервера не настраивается. Пропускаю."
    exit 0
fi

DOMAIN=$(getenv DOMAIN)
SSH_PORT=$(getenv SSH_PORT); SSH_PORT=${SSH_PORT:-54368}
BACKUP_DIR=$(getenv BACKUP_DIR); BACKUP_DIR=${BACKUP_DIR:-./backups}

CADDY_ADDR=$(docker compose port caddy 443 2>/dev/null | head -1)
CADDY_IP=${CADDY_ADDR%%:*}
[ -z "$CADDY_IP" ] || [ "$CADDY_IP" = "0.0.0.0" ] && CADDY_IP=127.0.0.1
curl_site() { curl -sk -m 10 --resolve "$DOMAIN:443:$CADDY_IP" "$@" ; }

echo "== 1. SSH: порт, root-логин, лимит попыток =="
SSHD_CFG=$(sshd -T 2>/dev/null)
# Именно слушающие сокеты, а не конфиг: при сокет-активации (Ubuntu 22.10+)
# `Port` в sshd_config игнорируется и порт остаётся 22.
PORTS=$(ss -ltnH 2>/dev/null | awk '{print $4}' | sed 's/.*://' | sort -u)
[ -n "$PORTS" ] || PORTS=$(echo "$SSHD_CFG" | awk '$1=="port"{print $2}')
echo "$PORTS" | grep -qx "$SSH_PORT" \
    && ok "sshd слушает нестандартный порт $SSH_PORT" \
    || fail "порт $SSH_PORT не слушается (открыты: $(echo "$PORTS" | tr '\n' ' '))"
if echo "$SSHD_CFG" | awk '$1=="port"{print $2}' | grep -qx 22 || echo "$PORTS" | grep -qx 22; then
    warn "порт 22 всё ещё открыт — после проверки входа: sudo ./setup-security.sh --drop-22"
else
    ok "стандартный порт 22 закрыт"
fi
case $(echo "$SSHD_CFG" | awk '$1=="permitrootlogin"{print $2}') in
    no) ok "вход под root по SSH запрещён" ;;
    "") warn "не удалось прочитать permitrootlogin (нужен root?)" ;;
    *)  fail "PermitRootLogin=$(echo "$SSHD_CFG" | awk '$1=="permitrootlogin"{print $2}') — нужен no" ;;
esac
MAXAUTH=$(echo "$SSHD_CFG" | awk '$1=="maxauthtries"{print $2}')
[ -n "$MAXAUTH" ] && [ "$MAXAUTH" -le 3 ] 2>/dev/null \
    && ok "лимит попыток авторизации SSH: $MAXAUTH" \
    || warn "MaxAuthTries=${MAXAUTH:-?} — ожидалось ≤3"

echo "== 2. Файрвол =="
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | head -1 | grep -q active; then
    ok "ufw активен"
    UFW_RULES=$(ufw status 2>/dev/null | awk 'NR>3 && $1 ~ /^[0-9]/ {print $1}' | cut -d/ -f1 | sort -u)
    EXTRA=$(echo "$UFW_RULES" | grep -v -e "^$SSH_PORT$" -e '^22$' -e '^80$' -e '^443$' || true)
    [ -z "$EXTRA" ] && ok "открыты только нужные порты: $(echo "$UFW_RULES" | tr '\n' ' ')" \
        || warn "лишние правила ufw: $(echo "$EXTRA" | tr '\n' ' ')"
else
    fail "ufw не активен — запусти sudo ./setup-security.sh"
fi

echo "== 3. Бан сканеров и перебора (fail2ban) =="
if command -v fail2ban-client >/dev/null 2>&1 && fail2ban-client ping >/dev/null 2>&1; then
    ok "fail2ban работает"
    for jail in sshd caddy-auth caddy-scan recidive; do
        if fail2ban-client status "$jail" >/dev/null 2>&1; then
            BANNED=$(fail2ban-client status "$jail" 2>/dev/null \
                | sed -n 's/.*Currently banned:[[:space:]]*//p' | head -1)
            ok "джейл $jail включён (в бане: ${BANNED:-0})"
        else
            fail "джейл $jail не включён"
        fi
    done
else
    fail "fail2ban не установлен или не запущен"
fi

echo "== 4. Внутренние сервисы не наружу =="
PUBLISHED=$(docker compose ps --format '{{.Service}} {{.Publishers}}' 2>/dev/null \
    | grep -v '^caddy ' | grep -o '0\.0\.0\.0:[0-9]*' | cut -d: -f2 | sort -u || true)
[ -z "$PUBLISHED" ] && ok "postgres/nats/minio доступны только внутри docker-сети" \
    || fail "наружу опубликованы порты внутренних сервисов: $(echo "$PUBLISHED" | tr '\n' ' ')"
LISTEN=$(ss -ltn 2>/dev/null | awk '{print $4}' | grep -E '^(0\.0\.0\.0|\[::\]):(5432|4222|9000|8222)$' || true)
[ -z "$LISTEN" ] && ok "на внешних интерфейсах нет 5432/4222/9000" \
    || fail "слушают наружу: $(echo "$LISTEN" | tr '\n' ' ')"

echo "== 5. TLS и редирект =="
ISSUER=$(echo | openssl s_client -connect "$CADDY_IP:443" -servername "$DOMAIN" 2>/dev/null \
    | openssl x509 -noout -issuer 2>/dev/null)
PUBLIC_CERT=no
case "$ISSUER" in
    *"Let's Encrypt"*) ok "сертификат Let's Encrypt (Caddy обновляет сам)"; PUBLIC_CERT=yes ;;
    *Caddy*) warn "self-signed (Caddy local CA) — снаружи домен недоступен или это стенд" ;;
    "") warn "сертификат не прочитан" ;;
    *) warn "issuer: $ISSUER"; PUBLIC_CERT=yes ;;
esac
# У локального CA срок жизни ~12 часов и обновляется он сам — считать дни бессмысленно.
if [ "$PUBLIC_CERT" = yes ]; then
    EXPIRES=$(echo | openssl s_client -connect "$CADDY_IP:443" -servername "$DOMAIN" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -n "$EXPIRES" ]; then
        LEFT=$(( ( $(date -d "$EXPIRES" +%s 2>/dev/null || echo 0) - $(date +%s) ) / 86400 ))
        [ "$LEFT" -gt 30 ] && ok "сертификат действует ещё $LEFT дн." \
            || warn "сертификат истекает через $LEFT дн. — проверь автообновление Caddy"
    fi
fi
REDIR=$(curl -s -m 10 -o /dev/null -w '%{http_code}' --resolve "$DOMAIN:80:$CADDY_IP" "http://$DOMAIN/")
case "$REDIR" in
    301|302|308) ok "HTTP → HTTPS редирект ($REDIR)" ;;
    *) fail "http://$DOMAIN/ вернул $REDIR вместо редиректа" ;;
esac

echo "== 6. Заголовки безопасности =="
HEADERS=$(curl_site -sI "https://$DOMAIN/")
for h in Strict-Transport-Security X-Content-Type-Options X-Frame-Options Referrer-Policy; do
    echo "$HEADERS" | grep -qi "^$h:" && ok "$h" || warn "нет заголовка $h"
done

echo "== 7. Rate limiting на входе =="
CODES=""
i=0
while [ $i -lt 15 ]; do
    C=$(curl_site -o /dev/null -w '%{http_code}' -X POST "https://$DOMAIN/api/auth/login" \
        -H 'Content-Type: application/json' -d '{"email":"verify@example.invalid","password":"x"}')
    CODES="$CODES $C"
    i=$((i+1))
done
case "$CODES" in
    *429*) ok "перебор пароля упирается в 429 (ответы:$CODES)" ;;
    *) fail "15 попыток логина подряд прошли без 429 (ответы:$CODES)" ;;
esac

echo "== 8. Блокировка сканеров =="
for p in /wp-login.php /.env /phpmyadmin/index.php; do
    C=$(curl_site -o /dev/null -w '%{http_code}' "https://$DOMAIN$p")
    case "$C" in
        403|404|444) ok "$p → $C" ;;
        *) fail "$p → $C (ожидался 403/404)" ;;
    esac
done
C=$(curl_site -o /dev/null -w '%{http_code}' -A "sqlmap/1.7" "https://$DOMAIN/")
case "$C" in
    403|404|444) ok "сканерский User-Agent отбит ($C)" ;;
    *) warn "запрос с User-Agent sqlmap вернул $C" ;;
esac

echo "== 9. Бэкапы =="
[ -f /etc/cron.d/std-cards ] && ok "кроны бэкапа установлены" || fail "нет /etc/cron.d/std-cards"
LAST=$(ls -t "$BACKUP_DIR"/std_cards_*.sql.gz 2>/dev/null | head -1)
if [ -n "$LAST" ]; then
    AGE=$(( ( $(date +%s) - $(stat -c %Y "$LAST" 2>/dev/null || echo 0) ) / 3600 ))
    [ "$AGE" -le 25 ] && ok "свежий дамп: $LAST ($AGE ч назад)" \
        || warn "последний дамп $AGE ч назад: $LAST"
    if [ -x ./verify-backup.sh ]; then
        ./verify-backup.sh >/dev/null 2>&1 && ok "бэкап восстанавливается" \
            || fail "бэкап НЕ восстанавливается (./verify-backup.sh)"
    fi
else
    # Сразу после установки дампов ещё нет — первый сделает крон в 03:00.
    warn "в $BACKUP_DIR пока нет дампов (первый создаст крон; вручную: docker compose run --rm backup)"
fi

echo ""
echo "Итог: OK=$PASS WARN=$WARN FAIL=$FAIL"
[ "$FAIL" -gt 0 ] && { echo "Есть проблемы — см. [FAIL] выше."; exit 1; }
echo "Требования ТЗ по безопасности выполнены."
