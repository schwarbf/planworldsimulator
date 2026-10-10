FROM node:24-slim AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY src/web/package.json src/web/package.json
RUN pnpm install --frozen-lockfile --filter @planbench/web...
COPY src/web src/web
RUN pnpm --filter @planbench/web run build

FROM nginx:1.29-alpine
COPY src/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/src/web/dist /usr/share/nginx/html
EXPOSE 80
