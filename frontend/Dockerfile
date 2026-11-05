FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

ARG VITE_OTEL_EXPORTER_OTLP_ENDPOINT=
ARG VITE_SAVORLOOP_ENVIRONMENT=local
ARG VITE_SAVORLOOP_VERSION=local
ENV VITE_OTEL_EXPORTER_OTLP_ENDPOINT=$VITE_OTEL_EXPORTER_OTLP_ENDPOINT \
    VITE_SAVORLOOP_ENVIRONMENT=$VITE_SAVORLOOP_ENVIRONMENT \
    VITE_SAVORLOOP_VERSION=$VITE_SAVORLOOP_VERSION

COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
