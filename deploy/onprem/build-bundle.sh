#!/bin/sh
# Сборка offline-бандла для установки на сервер заказчика.
# Запускать на машине с интернетом и docker buildx: ./build-bundle.sh
# Результат: dist/std-cards-onprem-<date>.tar.gz
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(git -C "$DIR" rev-parse --show-toplevel)
PROJECT="$ROOT/projects/std-cards"
PLATFORM=linux/amd64

echo "==> Сборка образов ($PLATFORM)"
docker build --platform "$PLATFORM" -t std-cards-api:prod "$PROJECT/backend"
docker build --platform "$PLATFORM" -t std-cards-frontend:prod "$PROJECT/frontend"
docker build --platform "$PLATFORM" -t std-cards-caddy:prod "$DIR/caddy"

echo "==> Pull инфраструктурных образов"
for img in postgres:16-alpine nats:2.10-alpine minio/minio:latest minio/mc:latest; do
    docker pull --platform "$PLATFORM" "$img"
done

echo "==> docker save"
STAGE=$(mktemp -d)
BUNDLE="$STAGE/std-cards-onprem"
mkdir -p "$BUNDLE/images"
docker save -o "$BUNDLE/images/std-cards-api.tar" std-cards-api:prod
docker save -o "$BUNDLE/images/std-cards-frontend.tar" std-cards-frontend:prod
docker save -o "$BUNDLE/images/std-cards-caddy.tar" std-cards-caddy:prod
docker save -o "$BUNDLE/images/infra.tar" \
    postgres:16-alpine nats:2.10-alpine minio/minio:latest minio/mc:latest

echo "==> Файлы бандла"
cp "$DIR/docker-compose.yml" "$DIR/Caddyfile" "$DIR/.env.example" "$DIR/README.md" "$BUNDLE/"
# install.sh зовёт setup-*.sh и postcheck.sh — без них offline-установка падает на середине
for s in install.sh update.sh preflight.sh postcheck.sh verify-backup.sh verify-security.sh \
         setup-cron.sh setup-autostart.sh setup-backup-disk.sh setup-security.sh; do
    cp "$DIR/$s" "$BUNDLE/"
    chmod +x "$BUNDLE/$s"
done
mkdir -p "$BUNDLE/caddy"
cp "$DIR/caddy/Dockerfile" "$BUNDLE/caddy/"

mkdir -p "$DIR/dist"
OUT="$DIR/dist/std-cards-onprem-$(date +%Y%m%d).tar.gz"
COPYFILE_DISABLE=1 tar -C "$STAGE" --no-xattrs -czf "$OUT" std-cards-onprem 2>/dev/null \
    || COPYFILE_DISABLE=1 tar -C "$STAGE" -czf "$OUT" std-cards-onprem
rm -rf "$STAGE"

echo ""
echo "Готово: $OUT"
du -h "$OUT"
echo "На сервере: tar xzf <бандл> && cd std-cards-onprem && sudo ./install.sh"
