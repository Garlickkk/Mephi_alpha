# Cabinet Backend

Бэкенд личного кабинета предпринимателя с кредитными продуктами. Состоит из трёх сервисов и PostgreSQL для каждого из них.

| Сервис | Язык / стек | Порт | База | Роль |
|--------|-------------|------|------|------|
| `user_server` | Kotlin, Spring Boot 4.1.2, JJWT | 8082 | PostgreSQL `localhost:5433`, БД `users` | регистрация, логин, выпуск JWT |
| `product_server` | Kotlin, Spring Boot 4.1.2 | 8081 | PostgreSQL `localhost:5432`, БД `products` | каталог кредитных продуктов |
| `application_server` | Java 21, Spring Boot 4.1.2, JJWT | 8083 | PostgreSQL `localhost:5434`, БД `applications` | заявки на кредит |
| decision service | не реализован | 8090 (ожидается) | — | решение по заявке, см. `application_server/docs/decision-service-api.md` |

## Схема взаимодействия

```
            ┌────────────┐  JWT (access)  ┌────────────────────┐
клиент ───▶ │ user_server│ ─────────────▶ │ application_server │ ──▶ product_server   (GET /products/{id})
(фронтенд)  │   :8082    │                │       :8083        │ ──▶ decision service (POST /api/v1/decisions)
            └────────────┘                └────────────────────┘ ◀── callback решения
                                                 ▲
клиент ───────────────────────────────────────── │ ── GET /api/v0/products (каталог, без токена)
                                                 ┘
```

Клиент получает access-токен в `user_server` и передаёт его в заголовке `Authorization: Bearer <token>` во все
остальные сервисы. Все три сервиса используют один секрет HS256, поэтому токен, выданный `user_server`,
принимается в `application_server` без обращения к нему.

Claims access-токена: `sub` (логин), `inn`, `organization_type` (`OOO`, `IP`, `AO`), `okved_main`,
`registration_date`, `authorities`, `type` (`access` или `refresh`).

## Требования

- Java 21
- Docker (для PostgreSQL)
- Maven через `./mvnw` в каждом сервисе (отдельной установки Maven не нужно)

## Запуск

### 1. Базы данных

```bash
docker run -d --name users-db -p 5433:5432 \
  -e POSTGRES_DB=users -e POSTGRES_USER=user -e POSTGRES_PASSWORD=user_pass postgres:16

docker run -d --name products-db -p 5432:5432 \
  -e POSTGRES_DB=products -e POSTGRES_USER=product_user -e POSTGRES_PASSWORD=product_pass postgres:16

docker run -d --name applications-db -p 5434:5432 \
  -e POSTGRES_DB=applications -e POSTGRES_USER=applications_user -e POSTGRES_PASSWORD=applications_pass postgres:16
```

Таблицы создаются автоматически (`spring.jpa.hibernate.ddl-auto=update`), миграций нет.

### 2. Сервисы

Порядок важен только для проверки сквозного сценария. Сами сервисы стартуют независимо.

```bash
cd user_server        && ./mvnw spring-boot:run   # :8082
cd product_server     && ./mvnw spring-boot:run   # :8081
cd application_server && ./mvnw spring-boot:run   # :8083
```

Сервис решений в репозитории не реализован. Пока его нет, `application_server` оставляет заявку в статусе
`UNDER_CONSIDERATION`. Для демонстрации можно поднять заглушку из раздела 9 `docs/decision-service-api.md`.

## Конфигурация

Все секреты и параметры подключения к БД можно переопределить переменными окружения. Значения по умолчанию нужны
только для локальной разработки.

| Переменная | Сервис | Значение по умолчанию в коде |
|------------|--------|------------------------------|
| `JWT_SECRET` | user_server, application_server | одинаковый секрет во всех сервисах, см. `application.properties` |
| `PRODUCT_SERVICE_URL` | application_server | `http://localhost:8081` |
| `DECISION_SERVICE_URL` | application_server | `http://localhost:8090` |
| `DECISION_TIMEOUT` | application_server | `5s` |
| `INTERNAL_SERVICE_TOKEN` | application_server | `change-me-internal-token` |
| `DB_URL`, `DB_USER`, `DB_PASSWORD` | user_server, product_server | см. `application.properties` |

`JWT_SECRET` должен быть одинаковым в `user_server` и `application_server`, иначе токены из одного сервиса
не примет другой.

## API по сервисам

Подробно: `user_server/README.md`, `product_server/README.md`, `application_server/README.md`.

| Сервис | Метод | Путь | Авторизация |
|--------|-------|------|-------------|
| user_server | POST | `/api/v0/auth/register` | нет |
| user_server | POST | `/api/v0/auth/login` | нет |
| user_server | POST | `/api/v0/auth/refresh` | нет |
| user_server | POST | `/api/v0/auth/logout` | Bearer |
| product_server | GET | `/products` | нет |
| product_server | GET | `/products/{id}` | нет |
| application_server | POST | `/api/v0/applications` | Bearer |
| application_server | GET | `/api/v0/applications` | Bearer |
| application_server | GET | `/api/v0/applications/{id}` | Bearer |
| application_server | POST | `/api/v0/applications/{id}/counter-offer` | Bearer |
| application_server | POST | `/api/v0/internal/applications/{id}/decision` | `X-Service-Token` (только для сервиса решений) |

`product_server` отдаёт `/products` и `/products/{id}`, без префикса `/api/v0`. `user_server` и
`application_server` используют префикс `/api/v0`.

## Сквозной сценарий

1. Зарегистрироваться в `user_server` (`POST /api/v0/auth/register`) и войти (`POST /api/v0/auth/login`). Сохранить `accessToken`.
2. Получить каталог: `GET http://localhost:8081/products`. Выбрать `id` продукта.
3. Подать заявку: `POST http://localhost:8083/api/v0/applications` с `Authorization: Bearer <accessToken>`
   и телом с `productId` и `calculator`.
4. Проверить статус: `GET http://localhost:8083/api/v0/applications/{id}`.
5. Если статус `COUNTER_OFFER`, ответить на предложение: `POST .../counter-offer` с `{"accept": true}`.

Примеры запросов и ответов для каждого шага — в README соответствующих сервисов.

## Состояние сервисов

Что готово и проверено только чтением кода, а не запуском:

- `user_server`: регистрация, логин, refresh, logout, `/users/me`, список и карточка пользователя (админ или сам
  пользователь). Ошибки возвращаются в формате `{message, dateTime}`: 400 для валидации, 401 для неверных
  учётных данных, 403 для недостатка прав. Ограничения: `ADMIN` назначается вручную в БД, миграций нет.
- `product_server`: только чтение каталога. `POST` и `PUT` описаны в DTO, но контроллер их не содержит.
- `application_server`: подача, просмотр, ответ на компромисс и callback решения. Повторной отправки заявок без
  решения нет, это нужно добавить планировщиком. Тест `ApplicationTests` требует запущенную базу.
- decision service: не реализован, описан API.

## Что ещё не сделано на уровне всего бэкенда

- Миграции БД вместо `ddl-auto=update`.
- Общий `docker-compose.yml` для баз и сервисов.
- Тесты, кроме пустых `contextLoads`.
- OpenAPI/Swagger, коллекция запросов и диаграмма состояний в отдельном файле. Диаграмма состояний заявки есть в README `application_server`.

Требования хакатона (THIRD_PARTY_NOTICES, OpenAPI, коллекция запросов, тестовые данные) этим README не закрываются, их нужно сделать отдельно.