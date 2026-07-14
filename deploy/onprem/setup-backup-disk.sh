#!/bin/sh
# Подключение отдельного диска под бэкапы БД.
# Показывает содержимое диска и спрашивает подтверждение ПЕРЕД форматированием.
# Запуск: sudo ./setup-backup-disk.sh /dev/sdX
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
MOUNT_POINT=/mnt/std-cards-backup

[ "$(id -u)" -eq 0 ] || { echo "ERROR: запускать от root (sudo $0 $*)" >&2; exit 1; }
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки" >&2; exit 1; }

DISK=${1:-}
if [ -z "$DISK" ]; then
    echo "Использование: sudo ./setup-backup-disk.sh /dev/sdX"
    echo ""
    echo "Доступные диски:"
    lsblk -d -o NAME,SIZE,MODEL,TYPE | grep disk
    exit 1
fi
[ -b "$DISK" ] || { echo "ERROR: $DISK не блочное устройство" >&2; exit 1; }

ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null || true)
if [ -n "$ROOT_DISK" ] && [ "$DISK" = "/dev/$ROOT_DISK" ]; then
    echo "ERROR: $DISK — системный диск, на нём стоит ОС. Отказ." >&2
    exit 1
fi

echo "==> Диск $DISK"
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT "$DISK"

echo ""
echo "==> Что на диске сейчас"
FOUND_DATA=0
TMP=$(mktemp -d)
for part in $(lsblk -lnpo NAME "$DISK" | tail -n +2); do
    fstype=$(lsblk -no FSTYPE "$part" | head -1)
    [ -n "$fstype" ] || continue
    if mount -o ro "$part" "$TMP" 2>/dev/null; then
        count=$(find "$TMP" -mindepth 1 -maxdepth 2 2>/dev/null | head -200 | wc -l)
        used=$(df -h "$TMP" | tail -1 | awk '{print $3}')
        echo "  $part ($fstype): занято $used, объектов в корне (до 2 уровней): $count"
        ls -A "$TMP" 2>/dev/null | head -12 | sed 's/^/      /'
        [ "$count" -gt 0 ] && FOUND_DATA=1
        umount "$TMP"
    else
        echo "  $part ($fstype): не смонтировался для просмотра"
    fi
done
rmdir "$TMP"

echo ""
if [ "$FOUND_DATA" = "1" ]; then
    echo "!!! НА ДИСКЕ ЕСТЬ ДАННЫЕ (см. выше). Форматирование удалит их безвозвратно."
else
    echo "Данных на диске не видно."
fi
echo "Диск будет размечен заново в ext4 и смонтирован в $MOUNT_POINT."
printf "Введите ровно 'ФОРМАТИРОВАТЬ' для продолжения: "
read -r CONFIRM
[ "$CONFIRM" = "ФОРМАТИРОВАТЬ" ] || { echo "Отменено, диск не тронут."; exit 1; }

echo "==> Размечаю $DISK"
for part in $(lsblk -lnpo NAME "$DISK" | tail -n +2); do
    umount "$part" 2>/dev/null || true
done
wipefs -a "$DISK"
parted -s "$DISK" mklabel gpt mkpart primary ext4 0% 100%
sleep 2
PART=$(lsblk -lnpo NAME "$DISK" | tail -n +2 | head -1)
mkfs.ext4 -F -L std-backup "$PART"

echo "==> Монтирую в $MOUNT_POINT"
UUID=$(blkid -s UUID -o value "$PART")
mkdir -p "$MOUNT_POINT"
grep -q "$UUID" /etc/fstab || printf 'UUID=%s %s ext4 defaults,nofail 0 2\n' "$UUID" "$MOUNT_POINT" >> /etc/fstab
mount "$MOUNT_POINT"
mkdir -p "$MOUNT_POINT/db"
chmod 700 "$MOUNT_POINT/db"

echo "==> Прописываю BACKUP_DIR в .env"
if grep -q '^BACKUP_DIR=' .env; then
    sed -i "s|^BACKUP_DIR=.*|BACKUP_DIR=$MOUNT_POINT/db|" .env
else
    printf '\n# Каталог для бэкапов БД (отдельный диск)\nBACKUP_DIR=%s/db\n' "$MOUNT_POINT" >> .env
fi

echo ""
df -h "$MOUNT_POINT" | tail -1
echo "Готово. Бэкапы будут писаться в $MOUNT_POINT/db"
echo "Проверить: sudo ./update.sh  (или docker compose run --rm backup)"
