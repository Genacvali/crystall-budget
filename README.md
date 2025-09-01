# CrystallBudget 💎

Минимальный budget management API + frontend для личного пользования.

## Шаги

1) Установи Node LTS, PostgreSQL, Caddy.
2) Создай каталог: /data/crystall-budget и скопируй проект.
3) API:
   ```bash
   cd api && cp .env.example .env  # поправь DATABASE_URL, JWT_SECRET
   npm i
   # один раз создай таблицу User в psql (см. server.js комментарий).
   sudo systemctl enable --now crystall-api
   ```
4) WEB:
   ```bash
   cd ../web
   npm i
   npm run build
   sudo systemctl enable --now crystall-web
   ```
5) Caddy: /etc/caddy/Caddyfile (подставь домен/sslip.io), затем:
   ```bash
   sudo systemctl reload caddy
   ```

## Создание таблицы User в PostgreSQL

```sql
create extension if not exists pgcrypto;
create table if not exists "User"(
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  "passwordHash" text not null
);
```