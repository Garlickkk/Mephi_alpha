# Backend кредитного кабинета

Четыре сервиса, три PostgreSQL. Единый Docker-запуск с каталогом и корректными связями описан в [корневом README](../README.md); это основной способ проверки для жюри.

| Сервис | Порт при запуске на хосте | Хранилище | Назначение |
|---|---|---|---|
| user_server | 8082 | PostgreSQL users, localhost:5433 | регистрация, вход, профиль, JWT |
| product_server | 8081 | PostgreSQL products, localhost:5432 | каталог |
| application_server | 8083 | PostgreSQL applications, localhost:5434 | заявки, история, статусы, callback |
| decision_service | 8090 | память процесса | скоринг, локальные моки, ручная проверка |

JVM-сервисы: Java 21, Spring Boot 4.1.2; user/product — Kotlin 2.3.21; user/application — JJWT 0.13.0. Скоринг: Python 3.11, FastAPI 0.115.6, Uvicorn 0.34.0, Pydantic 2.10.4. Maven 3.10.0 предоставляется wrapper.

## Запуск вне Docker Compose

Для каждого JVM-сервиса поднимите PostgreSQL по его README. Создание таблиц выполняет Hibernate (`ddl-auto=update`). Затем в отдельных терминалах из корня репозитория:

```bash
cd backend/user_server
sh ./mvnw spring-boot:run
```

```bash
cd backend/product_server
sh ./mvnw spring-boot:run
```

```bash
cd backend/application_server
sh ./mvnw spring-boot:run
```

```bash
cd backend/decision_service
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8090
```

Заполните каталог SQL из [demo/products.sql](../demo/products.sql). Примеры пользователей: [demo/README.md](../demo/README.md). Frontend вне Docker запускается своим Python proxy: [frontend/README.md](../frontend/README.md).

## Переменные окружения

| Переменная | Где используется |
|---|---|
| `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD` | все JVM-сервисы; стандартное переопределение Spring properties |
| `TEST_SECRET_KEY` | user_server, переопределяет `test.secret.key` |
| `JWT_SECRET` | application_server; значение должно совпадать с `TEST_SECRET_KEY` user_server |
| `TEST_ACCESS_TOKEN_EXPIRATION`, `TEST_REFRESH_TOKEN_EXPIRATION` | user_server; миллисекунды |
| `PRODUCT_SERVICE_URL` | application_server, по умолчанию http://localhost:8081 |
| `DECISION_SERVICE_URL` | application_server, по умолчанию http://localhost:8090 |
| `DECISION_TIMEOUT` | application_server, 5s |
| `INTERNAL_SERVICE_TOKEN` | application_server и decision_service; общий токен |
| `APPLICATION_SERVICE_URL` | decision_service, callback в http://localhost:8083 |

Произвольные `DB_URL`, `DB_USER`, `DB_PASSWORD` и `JWT_SECRET` в user_server сами по себе текущими properties не читаются. Для локальной демонстрации сохранены значения по умолчанию; для иной среды переопределите реальные ключи Spring, как делает корневой Compose.

## Контракты и ограничения

- [API](../docs/API.md), [OpenAPI](../docs/openapi.json), [API скоринга](../docs/decision-openapi.json), [Postman](../docs/requests.postman_collection.json).
- [Архитектура, данные и состояния](../docs/ARCHITECTURE.md), [сценарии](../docs/TEST_SCENARIOS.md).
- Подробные инструкции: [user_server](user_server/README.md), [product_server](product_server/README.md), [application_server](application_server/README.md), [decision_service](decision_service/README.md).

Сервис решений реализован. При его недоступности заявка остаётся UNDER_CONSIDERATION; автоматической повторной отправки нет. Очередь ручной проверки в памяти теряется при перезапуске. Миграций БД, персонального рабочего места сотрудника и промышленной отказоустойчивости нет.

У user_server отсутствуют ADMIN в enum, включение method security и общий обработчик ошибок. Собственный профиль доступен через `/api/v0/users/me`; не используйте админский URL для клиента. У product_server есть только GET, несмотря на DTO для изменения продуктов. Профильные frontend-тесты и тесты скоринга есть; `ApplicationTests` требуют БД.
