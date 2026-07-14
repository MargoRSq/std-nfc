#!/bin/sh
# Автозапуск стека при включении сервера: systemd-юнит + docker в автозагрузке.
# Идемпотентно. Вызывается из install.sh и update.sh, можно запускать отдельно:
#   sudo ./setup-autostart.sh
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
[ "$(id -u)" -eq 0 ] || { echo "ERROR: запускать от root" >&2; exit 1; }
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки" >&2; exit 1; }

command -v systemctl >/dev/null 2>&1 || { echo "  systemd нет — автозапуск пропущен"; exit 0; }

systemctl enable docker >/dev/null 2>&1 || true

BACKUP_DIR_VALUE=$(grep '^BACKUP_DIR=' .env | cut -d= -f2 || true)
REQUIRES_MOUNT=""
case "$BACKUP_DIR_VALUE" in
    /*) REQUIRES_MOUNT="RequiresMountsFor=$BACKUP_DIR_VALUE" ;;
esac

cat > /etc/systemd/system/std-cards.service <<EOF
[Unit]
Description=std-cards (docker compose)
Requires=docker.service
After=docker.service network-online.target
$REQUIRES_MOUNT

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DIR
ExecStart=$(command -v docker) compose up -d --wait --wait-timeout 300
ExecStop=$(command -v docker) compose stop
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable std-cards.service >/dev/null 2>&1
# Юнит oneshot+RemainAfterExit: помечаем активным, раз стек уже поднят,
# иначе systemd при следующем boot не увидит расхождения.
systemctl start std-cards.service >/dev/null 2>&1 || true
echo "  автозапуск включён (std-cards.service + docker)"
