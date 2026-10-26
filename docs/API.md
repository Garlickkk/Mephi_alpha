# API

Машиночитаемые контракты: [клиентские сервисы и callback](openapi.json), [скоринг](decision-openapi.json). Это снимки по контроллерам/DTO и main.py; при изменении кода их нужно обновлять. FastAPI также отдаёт `/openapi.json` и Swagger `/docs` на порту 8090. Java-сервисы пока не генерируют Swagger автоматически.

## Адреса и авторизация

В корневом Compose клиентские маршруты доступны через `http://localhost:8085`. Java-порты 8081–8083 доступны внутри сети. При запуске сервисов на хосте используются их собственные порты. Скоринг: `http://localhost:8090`, все `/api/v1/*` требуют `X-Service-Token`. Не отправляйте этот токен из клиентского интерфейса.

| Сервис | Метод и путь | Назначение / доступ |
|---|---|---|
| user | POST `/api/v0/auth/register` | регистрация, 201 + токены |
| user | POST `/api/v0/auth/login` | вход, 200 + токены |
| user | POST `/api/v0/auth/refresh` | refreshToken в теле, ротация |
| user | POST `/api/v0/auth/logout` | Bearer; отзыв refresh, 204 |
| user | GET `/api/v0/users/me` | Bearer; свой профиль |
| user | GET `/api/v0/users`, `/api/v0/users/{login}` | URL требует ADMIN; роль не выдаётся текущей моделью |
| product | GET `/products`, `/products/{id}` | публичный каталог / продукт |
| application | POST `/api/v0/applications` | Bearer, 201 + заявка |
| application | GET `/api/v0/applications?status=...` | только свои заявки |
| application | GET `/api/v0/applications/{id}` | чужой/отсутствующий id → 404 |
| application | POST `/api/v0/applications/{id}/counter-offer` | `{accept:true/false}`, только COUNTER_OFFER |
| application | POST `/api/v0/internal/applications/{id}/decision` | внутренний callback, X-Service-Token; не проксируется Nginx |
| decision | POST `/api/v1/decisions` | X-Service-Token, Idempotency-Key = applicationId |
| decision | GET `/api/v1/decisions?status=PENDING` | очередь ручной проверки |
| decision | GET `/api/v1/decisions/{decision_id}` | решение и доставка callback |
| decision | POST `/api/v1/decisions/{decision_id}/resolve` | решение сотрудника |
| decision | GET `/health` | публичная проверка доступности |

## Создание заявки

```json
{
  "productId": 1,
  "calculator": {
    "amount": 3000000,
    "durationYears": 3,
    "organizationType": "OOO",
    "collateral": false,
    "purpose": "Пополнение оборотных средств"
  }
}
```

`productId` берётся из каталога. С ним ставка определяется продуктом; без него требуется `calculator.rate`. Срок — целые годы, 1–30 с дополнительными лимитами продукта; сумма не менее 1000 и в пределах продукта. Тип организации должен совпадать с JWT. Финансовые показатели пользователь не вводит: их формирует локальный mock скоринга.

Ответ содержит id, статус, исходные условия, counterOffer, комментарий, даты и метрики скоринга. `counterOffer` частичный: `null` значит «без изменения». `APPROVED` скоринга отображается как `ACCEPTED` заявки. `PENDING` → `UNDER_CONSIDERATION`.

Клиентский POST не имеет идемпотентности. После timeout сначала проверьте историю. Внутренний POST скоринга идемпотентен по applicationId и fingerprint в пределах жизни процесса; тот же ключ с другим телом даёт 409.

## Ошибки и ограничения

application_server, product_server и decision_service используют `{message,dateTime}`. Для заявок: 400 — некорректные условия, 401 — токен, 404 — объект, 409 — состояние, 503 — недоступный каталог. Внутренний неверный токен даёт 403. В decision_service ошибки валидации преобразованы в 400.

У user_server нет общего обработчика ошибок; некорректная/повторная регистрация может дать 500, а тело Spring/Security отличается. Logout без токена также не следует считать корректно защищённым отдельным URL: `/auth/**` разрешён конфигурацией; рабочий клиент всегда отправляет Bearer. Эти ограничения нельзя скрывать общим описанием 400/401.

Примеры регистрации и пяти исходов: [demo/clients.json](../demo/clients.json). Запросы с сохранением переменных: [Postman](requests.postman_collection.json). Дополнительные детали: README каждого сервиса.
