# std-cards — установка на свой сервер (docker compose)

Полный стек одним скриптом: PostgreSQL 16, NATS JetStream, MinIO, API (FastAPI), worker,
frontend (nginx SPA), Caddy с автоматическим TLS (Let's Encrypt) и кроны обслуживания.

## Требования

| Что | Минимум | Рекомендуется |
|---|---|---|
| ОС | Linux x86_64 с Docker (Ubuntu 22.04/24.04, Debian 12) | Ubuntu Server 24.04 LTS |
| CPU / RAM | 2 vCPU / 4 GB | 4 vCPU / 8 GB |
| Диск | 100 GB SSD | 160+ GB SSD |
| Сеть | — | публичный IP, открытые порты **80 и 443** |
| DNS | — | A-запись домена → IP сервера |

Порты 80/443 и A-запись обязательны: NFC-карточки открываются из интернета,
Let's Encrypt валидирует домен по HTTP. Docker ставится скриптом автоматически.

## Установка (git clone → .env → скрипт)

```bash
git clone <репозиторий> && cd <репозиторий>/deploy/onprem

cp .env.example .env
vi .env          # задать DOMAIN=<ваш домен> и ACME_EMAIL=<email для Let's Encrypt>
                 # секреты можно не трогать — install.sh сгенерирует их сам

./preflight.sh   # проверка готовности: ресурсы, порты, DNS, интернет
sudo ./install.sh
sudo ./postcheck.sh   # проверка после установки: E2E логин → карточка → скан → бэкап
```

Скрипт делает всё остальное:
1. ставит Docker, если его нет;
2. собирает образы из исходников (или грузит offline-образы из `images/*.tar`, если они есть);
3. генерирует секреты вместо `CHANGE_ME` в `.env` (`openssl rand`);
4. поднимает весь стек и ждёт health-чеки (`docker compose up -d --wait`);
5. ставит кроны в `/etc/cron.d/std-cards`;
6. проверяет `/healthz` и `/readyz`, печатает адрес и логин супер-админа.

После установки: `https://<DOMAIN>/login`, супер-админ — `SEED_SUPER_ADMIN_EMAIL` /
`SEED_SUPER_ADMIN_PASSWORD` из `.env`. Сертификат Caddy получит сам при первом заходе.

## Offline-установка (сервер без интернета)

На машине с интернетом:

```bash
./build-bundle.sh    # соберёт amd64-образы и запакует всё в dist/std-cards-onprem-<дата>.tar.gz
```

Архив привезти на сервер, затем:

```bash
tar xzf std-cards-onprem-*.tar.gz && cd std-cards-onprem
cp .env.example .env && vi .env      # DOMAIN, ACME_EMAIL
sudo ./install.sh                    # найдёт images/*.tar и загрузит их вместо сборки
```

## Состав стека

| Сервис | Назначение |
|---|---|
| caddy | 80/443 наружу, авто-TLS Let's Encrypt |
| frontend | nginx: SPA + проксирование `/api/` и `/c/` на api |
| api | FastAPI/uvicorn :8000 (только внутри docker-сети) |
| worker | NATS-консьюмеры: импорт Excel, аналитика сканов |
| migrate | one-shot: `alembic upgrade head` + seed супер-админа |
| postgres | PostgreSQL 16, volume `pg-data` |
| nats | JetStream, volume `nats-data` |
| minio + minio-init | хранилище фото/импортов + бутстрап бакетов |

Кроны (`/etc/cron.d/std-cards`):
- **02:00 ежедневно** — партиции `scan_events` на следующий месяц;
- **03:00 ежедневно** — `pg_dump | gzip` в `./backups/`, ротация 30 дней.

## Эксплуатация

```bash
cd <...>/deploy/onprem
docker compose ps                          # статус
docker compose logs -f api worker          # логи
docker compose run --rm backup             # бэкап вручную → ./backups/
docker compose restart api worker          # рестарт приложения
```

**Обновление версии** (после `git pull`):

```bash
docker compose build && docker compose up -d
```

**Восстановление из бэкапа:**

```bash
docker compose stop api worker
gunzip -c backups/std_cards_<дата>.sql.gz | docker compose exec -T postgres psql -U std_cards -d std_cards
docker compose start api worker
```

Данные живут в docker volumes (`pg-data`, `minio-data`, `nats-data`) и `./backups`.
`.env` — единственный файл с секретами (chmod 600), сохраните его копию в надёжном месте.

## Диагностика

Первым делом: `sudo ./postcheck.sh` — прогоняет все проверки разом (контейнеры,
API, HTTPS, E2E-карточка, аналитика, кроны, бэкап) и показывает, что именно сломано.

| Симптом | Что смотреть |
|---|---|
| Сайт не открывается | `docker compose ps` — все healthy? `docker compose logs caddy` |
| Нет сертификата | A-запись указывает на сервер? Порты 80/443 открыты снаружи? `docker compose logs caddy` |
| 502 на `/api` | `docker compose logs api` — упал api или не прошли миграции (`docker compose logs migrate`) |
| Импорт «висит» | `docker compose logs worker` — воркер обрабатывает джобы |
| Проверить API изнутри | `docker compose exec api curl -s localhost:8000/readyz` |

## Важно

- **Домен фиксируется ДО прошивки NFC-тиража** — в чипы пишется полный URL
  `https://<домен>/c/<slug>`. Смена домена потом = перепрошивка всех карточек.
- Приложению интернет в рантайме не нужен (кроме продления сертификата Caddy).
- Если сервер за NAT — пробросить 80/443 с роутера. Без публичного доступа
  карточки не будут открываться у пользователей.
