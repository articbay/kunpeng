# =============================================================================
# Kunpeng 前端镜像：Node 构建 Vue 静态资源，Nginx 提供站点与 API 反代
# =============================================================================

FROM node:22-slim AS builder

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
