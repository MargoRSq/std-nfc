#!/bin/sh
# Обновление до актуальной версии: git pull → бэкап БД → пересборка → перезапуск.
# Запуск из каталога установки: sudo ./update.sh
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки"; exit 1; }

REPO_ROOT=$(CDPATH= cd -- "$DIR/../.." && pwd)

echo "==> 1/6 Обновление кода"
if [ -d "$REPO_ROOT/.git" ]; then
    git -C "$REPO_ROOT" pull --ff-only
    git -C "$REPO_ROOT" log -1 --oneline
else
    echo "  каталог не git-клон — пропускаю pull (offline-установка: замените файлы из нового бандла и перезапустите)"
fi

echo "==> 2/6 Бэкап БД перед обновлением"
mkdir -p backups
docker compose run --rm backup

echo "==> 3/6 Пересборка образов"
API_IMAGE=$(grep '^API_IMAGE=' .env | cut -d= -f2)
FRONTEND_IMAGE=$(grep '^FRONTEND_IMAGE=' .env | cut -d= -f2)
if [ -d "$REPO_ROOT/backend" ] && [ -d "$REPO_ROOT/frontend" ]; then
    docker build -t "${API_IMAGE:-std-cards-api:prod}" "$REPO_ROOT/backend"
    docker build -t "${FRONTEND_IMAGE:-std-cards-frontend:prod}" "$REPO_ROOT/frontend"
elif [ -d images ] && ls images/*.tar >/dev/null 2>&1; then
    for t in images/*.tar; do docker load -i "$t"; done
else
    echo "ERROR: нет ни исходников, ни images/*.tar" >&2
    exit 1
fi

echo "==> 4/6 Перезапуск (миграции применятся автоматически)"
docker compose up -d --wait --wait-timeout 300

echo "==> 5/6 Автозапуск и кроны (идемпотентно)"
./setup-autostart.sh
./setup-cron.sh

echo "==> 6/6 Проверка"
if [ -x ./postcheck.sh ]; then
    ./postcheck.sh
else
    docker compose exec -T api curl -fsS http://localhost:8000/readyz && echo " — api ready"
fi

echo ""
echo "Обновление завершено. Откат БД при проблемах: см. README (restore из backups/)."
