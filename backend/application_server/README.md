# Application Server (сервис заявок)

Принимает заявки на кредит от клиента личного кабинета, сохраняет их и возвращает текущий статус.
Решение о кредите принимает **сервис принятия решений** (отдельный сервис, в этом репозитории не реализован,
его ожидаемое API описано в `docs/decision-service-api.md`).

## Стек

- Java 21, Spring Boot 4.1.2 (Web MVC, Data JPA, Validation)
- PostgreSQL
- JJWT 0.13.0: проверка access-токенов, выпущенных `user_server`
- `RestClient`: вызовы `product_server` и сервиса принятия решений

## Место в системе

| Сервис | Порт | Роль |
|--------|------|------|
| user_server | 8082 | регистрация, логин, выпуск JWT |
| product_server | 8081 | каталог кредитных продуктов |
| **application_server** | **8083** | заявки (этот сервис) |
| decision service | 8090 (по умолчанию) | решение по заявке, см. `docs/decision-service-api.md` |

## Аутентификация

Клиент передаёт access-токен из `user_server`: `Authorization: Bearer <accessToken>`.
Из токена берутся claims: `sub` (логин), `inn`, `organization_type`, `okved_main`, `registration_date`.
Refresh-токены и токены с `type != access` отклоняются. Тип организации в калькуляторе должен совпадать с типом
из токена.

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `JWT_SECRET` | как в user_server | секрет HS256 для проверки токенов |
| `PRODUCT_SERVICE_URL` | `http://localhost:8081` | адрес product_server |
| `DECISION_SERVICE_URL` | `http://localhost:8090` | адрес сервиса принятия решений |
| `DECISION_TIMEOUT` | `5s` | таймаут вызова сервиса решений |
| `INTERNAL_SERVICE_TOKEN` | `change-me-internal-token` | общий секрет для callback'а решения (обязательно поменять) |

База: `jdbc:postgresql://localhost:5434/applications`, пользователь `applications_user`, пароль `applications_pass`
(см. `application.properties`). Таблица `credit_applications` создаётся автоматически (`ddl-auto=update`).

## Запуск

```bash
# PostgreSQL для сервиса заявок
docker run -d --name applications-db -p 5434:5432 \
  -e POSTGRES_DB=applications -e POSTGRES_USER=applications_user -e POSTGRES_PASSWORD=applications_pass \
  postgres:16

./mvnw spring-boot:run
```

## API

Базовый путь: `/api/v0`. Все эндпоинты, кроме `/internal/**`, требуют `Authorization: Bearer <accessToken>`.

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| POST | `/applications` | подать заявку | `201` + `ApplicationResponse` |
| GET | `/applications` | заявки клиента, опционально `?status=` | `200` + список |
| GET | `/applications/{id}` | одна заявка (только своя) | `200` + `ApplicationResponse` |
| POST | `/applications/{id}/counter-offer` | принять или отклонить компромиссные условия | `200` + `ApplicationResponse` |
| POST | `/internal/applications/{id}/decision` | callback сервиса решений (заголовок `X-Service-Token`) | `200` + `ApplicationResponse` |

### POST /applications

Два способа подачи:

1. **Готовый продукт**: передан `productId`. Сервис запрашивает продукт в product_server и проверяет сумму и срок
   по его лимитам. Ставка берётся из продукта.
2. **Калькулятор**: `productId` не передан. Ставка (`rate`) обязательна, ставка калькулятора сохраняется как есть.

```json
{
  "productId": 1,
  "calculator": {
    "rate": 12.5,
    "amount": 800000,
    "durationYears": 3,
    "organizationType": "OOO",
    "collateral": true,
    "purpose": "Пополнение оборотных средств"
  }
}
```

Поля `calculator`:

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `rate` | number | если нет `productId` | ставка, % годовых |
| `amount` | number | да | сумма, руб., не меньше 1000 |
| `durationYears` | integer | да | срок, лет, от 1 до 30 (в калькуляторе не было, добавлен, чтобы проверять лимиты продукта) |
| `organizationType` | `OOO`, `IP`, `AO` | да | должен совпадать с типом из токена |
| `collateral` | boolean | да | есть ли залог |
| `purpose` | string | да | цель кредита, до 500 символов |

Ответ `201 Created` (заголовок `Location` указывает на заявку):

```json
{
  "id": 17,
  "status": "UNDER_CONSIDERATION",
  "organizationType": "OOO",
  "productId": 1,
  "productTitle": "Потребительский кредит",
  "productInterest": 12.50,
  "rate": 12.50,
  "amount": 800000.00,
  "durationYears": 3,
  "purpose": "Пополнение оборотных средств",
  "collateral": true,
  "decisionComment": null,
  "counterOffer": null,
  "createdAt": "2026-10-25T10:12:31.114Z",
  "updatedAt": "2026-10-25T10:12:31.114Z"
}
```

Если сервис решений ответил сразу, статус уже итоговый. Если он недоступен или решение асинхронное,
заявка остаётся `UNDER_CONSIDERATION`, пока не придёт решение.

### GET /applications и GET /applications/{id}

Возвращают `ApplicationResponse`. Чужая заявка возвращает `404`, а не `403`, чтобы не раскрывать её существование.
Фильтр: `GET /applications?status=COUNTER_OFFER`.

### POST /applications/{id}/counter-offer

```json
{ "accept": true }
```

Доступно только для заявки в статусе `COUNTER_OFFER`. `accept: true` переводит заявку в `ACCEPTED`,
`accept: false` в `REJECTED`. Для других статусов возвращается `409`.

### Статусы

| Статус | Значение |
|--------|----------|
| `UNDER_CONSIDERATION` | на рассмотрении |
| `ACCEPTED` | принята (одобрена банком либо клиент принял компромиссные условия) |
| `REJECTED` | отклонена (отказ банка либо клиент отклонил компромиссные условия) |
| `COUNTER_OFFER` | банк предложил компромиссные условия, ждём ответа клиента |

Если статус `ACCEPTED` и поле `counterOffer` заполнено, итоговые условия кредита это `counterOffer`.



### Ошибки

Формат как в product_server: `{"message": "...", "dateTime": "2026-10-25T10:12:31"}`.

| Код | Когда |
|-----|-------|
| 400 | невалидное тело, сумма/срок вне лимитов продукта, несовпадение типа организации, нет ставки без продукта |
| 401 | нет или неверный JWT, либо передан не access-токен |
| 403 | неверный `X-Service-Token` на внутреннем эндпоинте |
| 404 | заявка или продукт не найдены |
| 409 | операция недопустима для текущего статуса |
| 503 | product_server недоступен |
| 500 | прочие ошибки (детали только в логах) |

## Сквозной сценарий для проверки

1. Регистрация и логин в user_server, получить `accessToken`.
2. `GET http://localhost:8081/products`: выбрать `id` продукта.
3. `POST /api/v0/applications` с `productId` и `calculator`: статус `UNDER_CONSIDERATION` (или сразу итоговый,
   если сервис решений доступен).
4. `GET /api/v0/applications/{id}`: получить текущий статус.
5. Если `COUNTER_OFFER`, `POST /api/v0/applications/{id}/counter-offer` с `{"accept": true}`.

## Известные ограничения

- Повторная отправка заявок, которые остались в `UNDER_CONSIDERATION` без решения, не реализована. Нужен планировщик.
- Callback защищён общим токеном, а не mTLS. Для продакшена нужно закрыть `/internal/**` на уровне сети.
- Тест `ApplicationTests.contextLoads` требует запущенный PostgreSQL.
