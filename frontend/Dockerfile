FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/10-resolver.sh /docker-entrypoint.d/10-resolver.sh
RUN chmod +x /docker-entrypoint.d/10-resolver.sh
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O- http://127.0.0.1/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
