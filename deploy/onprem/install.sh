#!/bin/sh
# Установка std-cards на голый Linux-сервер (Ubuntu/Debian, x86_64).
# Запускать из распакованного бандла: sudo ./install.sh
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: запускать от root (sudo ./install.sh)" >&2
    exit 1
fi

echo "==> 1/7 Docker"
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker не найден, ставлю с get.docker.com (нужен интернет)..."
    curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || {
    echo "ERROR: docker compose plugin не найден. apt install docker-compose-plugin" >&2
    exit 1
}

echo "==> 2/7 Образы"
BACKEND_DIR=$DIR/../../backend
FRONTEND_DIR=$DIR/../../frontend
if [ -d images ] && ls images/*.tar >/dev/null 2>&1; then
    for t in images/*.tar; do
        echo "  docker load < $t"
        docker load -i "$t"
    done
elif [ -f "$BACKEND_DIR/Dockerfile" ] && [ -f "$FRONTEND_DIR/Dockerfile" ]; then
    echo "  offline-образов нет — собираю из исходников (нужен интернет)"
    docker build -t std-cards-api:prod "$BACKEND_DIR"
    docker build -t std-cards-frontend:prod "$FRONTEND_DIR"
else
    echo "ERROR: нет ни images/*.tar, ни исходников backend/frontend рядом с бандлом" >&2
    exit 1
fi

echo "==> 3/7 Конфигурация (.env)"
if [ ! -f .env ]; then
    cp .env.example .env
fi
# Генерация секретов вместо CHANGE_ME (hex — безопасно для URL)
gen() { openssl rand -hex "$1"; }
for var in POSTGRES_PASSWORD:24 JWT_SECRET:48 MINIO_ACCESS_KEY:12 MINIO_SECRET_KEY:24 SEED_SUPER_ADMIN_PASSWORD:12; do
    name=${var%%:*}
    len=${var##*:}
    if grep -q "^${name}=CHANGE_ME$" .env; then
        val=$(gen "$len")
        sed -i "s|^${name}=CHANGE_ME$|${name}=${val}|" .env
        echo "  сгенерирован $name"
    fi
done
chmod 600 .env

if grep -q '^DOMAIN=cards.example.ru$' .env; then
    echo ""
    echo "ERROR: задай реальный домен в .env (DOMAIN=...) и ACME_EMAIL, затем перезапусти ./install.sh" >&2
    exit 1
fi

echo "==> 4/7 Запуск"
mkdir -p backups
docker compose up -d --wait --wait-timeout 300

echo "==> 5/7 Кроны (партиции + бэкап БД)"
cat > /etc/cron.d/std-cards <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 2 * * * root cd $DIR && docker compose run --rm partitions >> /var/log/std-cards-cron.log 2>&1
0 3 * * * root cd $DIR && docker compose run --rm backup >> /var/log/std-cards-cron.log 2>&1
EOF
chmod 644 /etc/cron.d/std-cards

echo "==> 6/7 Автозапуск при включении сервера"
./setup-autostart.sh

echo "==> 7/7 Проверка"
docker compose ps
docker compose exec -T api curl -fsS http://localhost:8000/healthz && echo " — api OK"
docker compose exec -T api curl -fsS http://localhost:8000/readyz && echo " — api ready"

DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)
ADMIN_EMAIL=$(grep '^SEED_SUPER_ADMIN_EMAIL=' .env | cut -d= -f2)
echo ""
echo "Готово: https://${DOMAIN}"
echo "Супер-админ: ${ADMIN_EMAIL} (пароль — SEED_SUPER_ADMIN_PASSWORD в $DIR/.env)"
echo "Сертификат Let's Encrypt Caddy получит сам при первом заходе (нужны открытые 80/443 и A-запись на этот сервер)."
