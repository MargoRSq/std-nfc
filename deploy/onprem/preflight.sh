#!/bin/sh
# Проверка готовности сервера ПЕРЕД установкой std-cards.
# Запуск: ./preflight.sh  (root не обязателен; .env читается, если уже создан)
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PASS=0; WARN=0; FAIL=0

ok()   { PASS=$((PASS+1)); printf '  [ OK ] %s\n' "$1"; }
warn() { WARN=$((WARN+1)); printf '  [WARN] %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf '  [FAIL] %s\n' "$1"; }

echo "== 1. Система =="
[ "$(uname -s)" = "Linux" ] && ok "ОС: Linux" || fail "ОС не Linux: $(uname -s)"
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ok "Архитектура: x86_64" || fail "Архитектура $ARCH — образы собраны под x86_64"

CORES=$(nproc 2>/dev/null || echo 0)
if [ "$CORES" -ge 4 ]; then ok "CPU: $CORES ядер"
elif [ "$CORES" -ge 2 ]; then warn "CPU: $CORES ядер (рекомендуется 4+)"
else fail "CPU: $CORES ядер (минимум 2)"; fi

RAM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
if [ "$RAM_MB" -ge 7500 ]; then ok "RAM: ${RAM_MB} MB"
elif [ "$RAM_MB" -ge 3800 ]; then warn "RAM: ${RAM_MB} MB (рекомендуется 8 GB)"
else fail "RAM: ${RAM_MB} MB (минимум 4 GB)"; fi

DISK_GB=$(df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc '0-9')
if [ "${DISK_GB:-0}" -ge 150 ]; then ok "Диск: ${DISK_GB} GB свободно"
elif [ "${DISK_GB:-0}" -ge 80 ]; then warn "Диск: ${DISK_GB} GB свободно (рекомендуется 160+)"
else fail "Диск: ${DISK_GB:-?} GB свободно (минимум ~100)"; fi

echo "== 2. Docker =="
if command -v docker >/dev/null 2>&1; then
    ok "Docker: $(docker --version | head -c 40)"
    docker compose version >/dev/null 2>&1 && ok "docker compose plugin есть" \
        || fail "docker compose plugin отсутствует (apt install docker-compose-plugin)"
    docker info >/dev/null 2>&1 && ok "docker daemon доступен" \
        || warn "docker daemon недоступен текущему пользователю (запускай install.sh через sudo)"
else
    warn "Docker не установлен — install.sh поставит его сам (нужен интернет)"
fi

echo "== 3. Порты 80/443 =="
for P in 80 443; do
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$P\$"; then
        fail "порт $P уже занят: $(ss -ltnp 2>/dev/null | grep -E "[:.]$P " | head -1 | grep -oE 'users:.*' | head -c 60)"
    else
        ok "порт $P свободен"
    fi
done

echo "== 4. Интернет =="
if curl -fsS -m 10 -o /dev/null https://registry-1.docker.io/v2/ 2>/dev/null || [ "$(curl -s -m 10 -o /dev/null -w '%{http_code}' https://registry-1.docker.io/v2/)" = "401" ]; then
    ok "docker registry доступен"
else
    OFFLINE=1
    if ls "$DIR"/images/*.tar >/dev/null 2>&1; then
        warn "интернета нет, но есть offline-образы images/*.tar"
    else
        fail "нет интернета и нет offline-образов — установка невозможна"
    fi
fi

echo "== 5. Конфигурация и домен =="
if [ ! -f "$DIR/.env" ]; then
    warn ".env ещё не создан (cp .env.example .env; задать DOMAIN и ACME_EMAIL)"
else
    DOMAIN=$(grep '^DOMAIN=' "$DIR/.env" | cut -d= -f2)
    ACME_EMAIL=$(grep '^ACME_EMAIL=' "$DIR/.env" | cut -d= -f2)
    if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "cards.example.ru" ]; then
        fail "DOMAIN в .env не задан"
    else
        ok "DOMAIN=$DOMAIN"
        RESOLVED=$(getent hosts "$DOMAIN" 2>/dev/null | awk '{print $1}' | head -1)
        if [ -z "$RESOLVED" ]; then
            fail "DNS: $DOMAIN не резолвится — добавьте A-запись на IP этого сервера"
        else
            EXT_IP=$(curl -fsS -m 8 https://api.ipify.org 2>/dev/null || echo "")
            LOCAL_IPS=$(hostname -I 2>/dev/null || echo "")
            if [ -n "$EXT_IP" ] && [ "$RESOLVED" = "$EXT_IP" ]; then
                ok "DNS: $DOMAIN → $RESOLVED (совпадает с внешним IP)"
            elif echo " $LOCAL_IPS " | grep -q " $RESOLVED "; then
                ok "DNS: $DOMAIN → $RESOLVED (локальный IP сервера)"
            else
                warn "DNS: $DOMAIN → $RESOLVED, внешний IP сервера: ${EXT_IP:-?} — если сервер за NAT, нужен проброс 80/443"
            fi
        fi
        [ -n "$ACME_EMAIL" ] && [ "$ACME_EMAIL" != "admin@example.ru" ] \
            && ok "ACME_EMAIL=$ACME_EMAIL" || fail "ACME_EMAIL в .env не задан"
    fi
fi

echo ""
echo "Итог: OK=$PASS WARN=$WARN FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "Есть блокирующие проблемы — исправьте [FAIL] и запустите снова."
    exit 1
fi
echo "Сервер готов к установке: sudo ./install.sh"
