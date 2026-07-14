#!/bin/sh
# Проверка ПОСЛЕ установки: стек поднят, API/фронт/публичная карточка/NATS/кроны работают.
# Запуск из каталога бандла: sudo ./postcheck.sh
set -u

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
PASS=0; WARN=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  [ OK ] %s\n' "$1"; }
warn() { WARN=$((WARN+1)); printf '  [WARN] %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf '  [FAIL] %s\n' "$1"; }

[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки"; exit 1; }
DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)
ADMIN_EMAIL=$(grep '^SEED_SUPER_ADMIN_EMAIL=' .env | cut -d= -f2)
ADMIN_PASS=$(grep '^SEED_SUPER_ADMIN_PASSWORD=' .env | cut -d= -f2)

echo "== 1. Контейнеры =="
BAD=$(docker compose ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null \
    | awk '$2 != "running" || ($3 != "" && $3 != "healthy") {print $1"("$2"/"$3")"}')
if [ -z "$BAD" ]; then
    ok "все сервисы running/healthy: $(docker compose ps --format '{{.Service}}' | tr '\n' ' ')"
else
    fail "проблемные сервисы: $BAD"
fi
for ONESHOT in migrate minio-init; do
    RC=$(docker inspect -f '{{.State.ExitCode}}' "std-cards-${ONESHOT}-1" 2>/dev/null || echo "?")
    [ "$RC" = "0" ] && ok "$ONESHOT завершился успешно" || fail "$ONESHOT exit code: $RC (docker compose logs $ONESHOT)"
done

echo "== 2. API изнутри =="
docker compose exec -T api curl -fsS -m 5 http://localhost:8000/healthz >/dev/null 2>&1 \
    && ok "api /healthz" || fail "api /healthz не отвечает"
docker compose exec -T api curl -fsS -m 5 http://localhost:8000/readyz >/dev/null 2>&1 \
    && ok "api /readyz (БД доступна)" || fail "api /readyz — проверь postgres и миграции"

echo "== 3. HTTPS снаружи (через Caddy) =="
CADDY_ADDR=$(docker compose port caddy 443 2>/dev/null | head -1)
CADDY_IP=${CADDY_ADDR%%:*}
[ "$CADDY_IP" = "0.0.0.0" ] && CADDY_IP=127.0.0.1
CODE=$(curl -sk -m 15 --resolve "$DOMAIN:443:$CADDY_IP" -o /dev/null -w '%{http_code}' "https://$DOMAIN/")
[ "$CODE" = "200" ] && ok "https://$DOMAIN/ → 200" || fail "https://$DOMAIN/ → $CODE (docker compose logs caddy frontend)"
ISSUER=$(echo | openssl s_client -connect "$CADDY_IP:443" -servername "$DOMAIN" 2>/dev/null \
    | openssl x509 -noout -issuer 2>/dev/null | head -c 100)
case "$ISSUER" in
    *"Let's Encrypt"*) ok "TLS-сертификат: Let's Encrypt" ;;
    *Caddy*)           warn "TLS: self-signed (Caddy local CA) — Let's Encrypt ещё не выдан или домен недоступен снаружи" ;;
    "")                warn "TLS: не удалось прочитать сертификат" ;;
    *)                 warn "TLS issuer: $ISSUER" ;;
esac

echo "== 4. E2E: логин → карточка → публичная страница =="
SLUG="postcheck-$(date +%s)"
TOK=$(curl -sk -m 10 --resolve "$DOMAIN:443:$CADDY_IP" -X POST "https://$DOMAIN/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}" \
    | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
if [ -z "$TOK" ]; then
    fail "логин супер-админом не прошёл ($ADMIN_EMAIL) — если пароль меняли, проверка E2E пропущена"
else
    ok "логин супер-админом"
    CARD=$(curl -sk -m 10 --resolve "$DOMAIN:443:$CADDY_IP" -X POST "https://$DOMAIN/api/cards/" \
        -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
        -d "{\"last_name\":\"Постчек\",\"first_name\":\"Тест\",\"membership_no\":\"pc-$$\",\"public_slug\":\"$SLUG\"}")
    CARD_ID=$(echo "$CARD" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
    if [ -z "$CARD_ID" ]; then
        fail "создание карточки: $(echo "$CARD" | head -c 120)"
    else
        ok "карточка создана"
        PC=$(curl -sk -m 10 --resolve "$DOMAIN:443:$CADDY_IP" -o /dev/null -w '%{http_code}' "https://$DOMAIN/c/$SLUG")
        [ "$PC" = "200" ] && ok "публичная страница /c/$SLUG → 200" || fail "публичная страница → $PC"
        OGT=$(curl -sk -m 20 --resolve "$DOMAIN:443:$CADDY_IP" -o /dev/null -w '%{content_type}' "https://$DOMAIN/c/$SLUG/og.png")
        case "$OGT" in image/png*) ok "OG-превью /c/$SLUG/og.png → image/png" ;; *) fail "og.png → $OGT (ожидался image/png)" ;; esac
        sleep 3
        SCANS=$(docker compose exec -T postgres psql -U std_cards -d std_cards -tAc \
            "select count(*) from scan_events" 2>/dev/null | tr -dc '0-9')
        [ "${SCANS:-0}" -ge 1 ] && ok "скан засчитан в аналитике (NATS+worker работают)" \
            || warn "скан не появился в scan_events — проверь worker: docker compose logs worker"
        curl -sk -m 10 --resolve "$DOMAIN:443:$CADDY_IP" -X DELETE "https://$DOMAIN/api/cards/$CARD_ID" \
            -H "Authorization: Bearer $TOK" -o /dev/null -w '' && ok "тестовая карточка удалена"
    fi
fi

echo "== 5. Кроны и бэкап =="
[ -f /etc/cron.d/std-cards ] && ok "кроны установлены (/etc/cron.d/std-cards)" \
    || fail "кроны не установлены — перезапусти install.sh"
if docker compose run --rm backup >/dev/null 2>&1; then
    LAST=$(ls -t backups/std_cards_*.sql.gz 2>/dev/null | head -1)
    [ -n "$LAST" ] && ok "бэкап работает: $LAST ($(du -h "$LAST" | cut -f1))" || fail "бэкап отработал, но файла нет в ./backups"
else
    fail "бэкап не отработал: docker compose run --rm backup"
fi

echo ""
echo "Итог: OK=$PASS WARN=$WARN FAIL=$FAIL"
[ "$FAIL" -gt 0 ] && { echo "Есть проблемы — см. [FAIL] выше."; exit 1; }
echo "Установка полностью работоспособна: https://$DOMAIN"
