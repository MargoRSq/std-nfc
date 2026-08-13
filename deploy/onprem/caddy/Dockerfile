# Caddy с модулем rate_limit — нужен для лимитов из ТЗ по безопасности.
# Ванильный образ директиву rate_limit не знает и падает на старте.
FROM caddy:2-builder-alpine AS builder
RUN xcaddy build --with github.com/mholt/caddy-ratelimit

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
