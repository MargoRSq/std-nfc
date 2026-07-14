#!/bin/sh
# Сборка offline-бандла для установки на сервер заказчика.
# Запускать на машине с интернетом и docker buildx: ./build-bundle.sh
# Результат: dist/std-cards-onprem-<date>.tar.gz
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT=$(CDPATH= cd -- "$DIR/../.." && pwd)
PLATFORM=linux/amd64

echo "==> Сборка образов ($PLATFORM)"
docker build --platform "$PLATFORM" -t std-cards-api:prod "$PROJECT/backend"
docker build --platform "$PLATFORM" -t std-cards-frontend:prod "$PROJECT/frontend"

echo "==> Pull инфраструктурных образов"
for img in postgres:16-alpine nats:2.10-alpine minio/minio:latest minio/mc:latest caddy:2-alpine; do
    docker pull --platform "$PLATFORM" "$img"
done

echo "==> docker save"
STAGE=$(mktemp -d)
BUNDLE="$STAGE/std-cards-onprem"
mkdir -p "$BUNDLE/images"
docker save -o "$BUNDLE/images/std-cards-api.tar" std-cards-api:prod
docker save -o "$BUNDLE/images/std-cards-frontend.tar" std-cards-frontend:prod
docker save -o "$BUNDLE/images/infra.tar" \
    postgres:16-alpine nats:2.10-alpine minio/minio:latest minio/mc:latest caddy:2-alpine

echo "==> Файлы бандла"
cp "$DIR/docker-compose.yml" "$DIR/Caddyfile" "$DIR/.env.example" \
   "$DIR/install.sh" "$DIR/preflight.sh" "$DIR/postcheck.sh" "$DIR/README.md" "$BUNDLE/"
chmod +x "$BUNDLE/install.sh" "$BUNDLE/preflight.sh" "$BUNDLE/postcheck.sh"

mkdir -p "$DIR/dist"
OUT="$DIR/dist/std-cards-onprem-$(date +%Y%m%d).tar.gz"
COPYFILE_DISABLE=1 tar -C "$STAGE" --no-xattrs -czf "$OUT" std-cards-onprem 2>/dev/null \
    || COPYFILE_DISABLE=1 tar -C "$STAGE" -czf "$OUT" std-cards-onprem
rm -rf "$STAGE"

echo ""
echo "Готово: $OUT"
du -h "$OUT"
echo "На сервере: tar xzf <бандл> && cd std-cards-onprem && sudo ./install.sh"
