#!/bin/sh
# nginx резолвит upstream один раз при старте и кеширует IP навсегда.
# Пересоздание контейнера api (compose up / rollout) меняет IP → 502 до рестарта nginx.
# Пишем resolver из /etc/resolv.conf (docker DNS 127.0.0.11 или kube-dns) — с ним
# proxy_pass через переменную резолвит имя на каждый запрос.
set -eu

NS=$(awk '/^nameserver/ { print $2; exit }' /etc/resolv.conf 2>/dev/null || true)
if [ -z "$NS" ]; then
    echo "10-resolver.sh: nameserver не найден, оставляю статический upstream" >&2
    exit 0
fi
case "$NS" in
    *:*) NS="[$NS]" ;;
esac

printf 'resolver %s valid=10s ipv6=off;\n' "$NS" > /etc/nginx/conf.d/00-resolver.conf
echo "10-resolver.sh: resolver $NS"
