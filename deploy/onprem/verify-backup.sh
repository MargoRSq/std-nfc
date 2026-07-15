#!/bin/sh
# Проверка, что из последнего бэкапа реально можно поднять БД.
# Восстанавливает дамп во ВРЕМЕННУЮ базу, сверяет содержимое, удаляет её.
# Боевую БД не трогает. Запуск: sudo ./verify-backup.sh
#
# Зачем: файл бэкапа может лежать, gzip -t проходить, а восстановление —
# падать (так было с immutable_unaccent и пустым search_path у pg_dump).
# Единственное доказательство рабочего бэкапа — восстановление.
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"
[ -f .env ] || { echo "ERROR: нет .env — запускать из каталога установки" >&2; exit 1; }

TMP_DB=verify_restore_$$
LOG=/tmp/std-cards-verify-$$.log
BACKUP_DIR=$(grep '^BACKUP_DIR=' .env | cut -d= -f2)
BACKUP_DIR=${BACKUP_DIR:-./backups}

psql_db() { docker compose exec -T postgres psql -U std_cards -d "$1" "$@" 2>/dev/null; }
q() { docker compose exec -T postgres psql -U std_cards -d "$TMP_DB" -tAc "$1" 2>/dev/null | tr -d '[:space:]'; }
cleanup() {
    docker compose exec -T postgres psql -U std_cards -d postgres \
        -c "DROP DATABASE IF EXISTS $TMP_DB" >/dev/null 2>&1 || true
    rm -f "$LOG"
}
trap cleanup EXIT

LAST=$(ls -t "$BACKUP_DIR"/std_cards_*.sql.gz 2>/dev/null | head -1 || true)
[ -n "$LAST" ] || { echo "FAIL: в $BACKUP_DIR нет бэкапов" >&2; exit 1; }
echo "Проверяю: $LAST ($(du -h "$LAST" | cut -f1))"

gzip -t "$LAST" || { echo "FAIL: архив битый" >&2; exit 1; }

docker compose exec -T postgres psql -U std_cards -d postgres \
    -c "DROP DATABASE IF EXISTS $TMP_DB" >/dev/null 2>&1
docker compose exec -T postgres psql -U std_cards -d postgres \
    -c "CREATE DATABASE $TMP_DB" >/dev/null 2>&1

zcat "$LAST" | docker compose exec -T postgres psql -U std_cards -d "$TMP_DB" >"$LOG" 2>&1 || true

ERRORS=$(grep -c '^ERROR' "$LOG" || true)
TABLES=$(q "select count(*) from information_schema.tables where table_schema='public'")
HAS_CARDS=$(q "select count(*) from information_schema.tables where table_name='cards'")
MIGRATION=$(q "select version_num from alembic_version")

FAILED=0
if [ "${ERRORS:-1}" != "0" ]; then
    echo "FAIL: $ERRORS ошибок при восстановлении:" >&2
    grep '^ERROR' "$LOG" | sort -u | head -5 >&2
    FAILED=1
fi
[ "${HAS_CARDS:-0}" = "1" ] || { echo "FAIL: таблица cards не восстановилась" >&2; FAILED=1; }
[ "${TABLES:-0}" -ge 15 ] 2>/dev/null || { echo "FAIL: восстановлено таблиц: ${TABLES:-0}, ожидалось 15+" >&2; FAILED=1; }
[ -n "$MIGRATION" ] || { echo "FAIL: нет alembic_version — схема неполная" >&2; FAILED=1; }

if [ "$FAILED" = "1" ]; then
    echo "БЭКАП НЕВОССТАНОВИМ. Не полагайтесь на него." >&2
    exit 1
fi

CARDS=$(q "select count(*) from cards")
USERS=$(q "select count(*) from users")
echo "OK: восстановлено без ошибок — таблиц $TABLES, карточек $CARDS, пользователей $USERS, миграция $MIGRATION"
