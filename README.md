# std-nfc

Электронные удостоверения членов СТД РФ: NFC-карточки с публичными страницами,
админ-панель, массовый импорт из Excel, аналитика сканирований.

- **backend/** — API (Python 3.13, FastAPI, SQLAlchemy 2, Alembic) + фоновый worker
- **frontend/** — SPA админ-панели (React 19, Vite, Tailwind) + nginx
- **deploy/onprem/** — установка на свой сервер одним скриптом (docker compose)

## Быстрый старт (свой сервер)

Нужен Linux x86_64 сервер (Ubuntu 22.04/24.04, 4 vCPU / 8 GB / 160 GB SSD),
домен с A-записью на сервер и открытые порты 80/443.

```bash
git clone https://github.com/MargoRSq/std-nfc.git && cd std-nfc/deploy/onprem

cp .env.example .env
vi .env            # DOMAIN=<ваш домен>, ACME_EMAIL=<email> — секреты сгенерируются сами

./preflight.sh     # проверка сервера: ресурсы, порты, DNS, интернет
sudo ./install.sh  # docker → сборка образов → секреты → запуск → кроны
sudo ./postcheck.sh  # E2E-проверка: логин → карточка → публичная страница → бэкап
```

После установки: `https://<домен>/login`, супер-админ — `SEED_SUPER_ADMIN_EMAIL` /
`SEED_SUPER_ADMIN_PASSWORD` из `deploy/onprem/.env`. TLS-сертификат Let's Encrypt
выпускается автоматически (Caddy).

## Обновление до новой версии

```bash
cd std-nfc/deploy/onprem
sudo ./update.sh    # git pull → бэкап БД → пересборка → перезапуск → проверка
```

Полная инструкция, offline-установка (сервер без интернета), эксплуатация, бэкапы
и диагностика: **[deploy/onprem/README.md](deploy/onprem/README.md)**.

## Что внутри стека

PostgreSQL 16 · NATS JetStream · MinIO · FastAPI API ×N · worker (импорт/аналитика)
· nginx SPA · Caddy (авто-TLS) · кроны: партиции БД + ежедневный `pg_dump`-бэкап.

## Разработка

```bash
# Backend
cd backend && rye sync && rye run lint && rye run test

# Frontend
cd frontend && npm install && npm run dev
```
