#!/bin/sh
# Регулярные задачи: партиции, бэкап БД, проверка восстановимости бэкапа.
# Идемпотентно, перезаписывает /etc/cron.d/std-cards целиком.
# Вызывается из install.sh и update.sh, можно запускать отдельно:
#   sudo ./setup-cron.sh
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
[ "$(id -u)" -eq 0 ] || { echo "ERROR: запускать от root" >&2; exit 1; }
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки" >&2; exit 1; }

cat > /etc/cron.d/std-cards <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# партиции scan_events на следующий месяц
0 2 * * * root cd $DIR && docker compose run --rm partitions >> /var/log/std-cards-cron.log 2>&1
# бэкап БД (ротация 30 дней внутри задачи)
0 3 * * * root cd $DIR && docker compose run --rm backup >> /var/log/std-cards-cron.log 2>&1
# проверка, что из бэкапа реально поднимается БД
30 4 * * 1 root cd $DIR && ./verify-backup.sh >> /var/log/std-cards-cron.log 2>&1
EOF
chmod 644 /etc/cron.d/std-cards
echo "  кроны: партиции 02:00, бэкап 03:00, проверка восстановимости пн 04:30"
