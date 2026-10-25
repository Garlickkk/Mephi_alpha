# Реальная интеграция backend, 26.10.2026
Источник: код контроллеров и DTO архива Mephi_alpha-backend_branch 2.zip (приоритет над прежней предлагаемой схемой).

| Назначение | Метод и путь | Сервис |
|---|---|---|
| Вход / регистрация | POST /api/v0/auth/login, /register | 8082 |
| Обновление / выход | POST /api/v0/auth/refresh, /logout | 8082 |
| Профиль | GET /api/v0/users/{login} | 8082 |
| Каталог | GET /products → {products:[…]} | 8081 |
| Создание / история | POST / GET /api/v0/applications | 8083 |
| Статус | GET /api/v0/applications/{id} | 8083 |
| Встречное предложение | POST /api/v0/applications/{id}/counter-offer {accept:boolean} | 8083 |

Bearer accessToken добавляется адаптером api.js. Не используется несуществующий /me. Авторизация только реальная. Выход очищает локальные токены даже при недоступном сервисе; серверная инвалидизация в таком случае не подтверждается.

Заявка: {productId:number,calculator:{amount:number,durationYears:integer,organizationType:OOO|IP|AO,collateral:boolean,purpose:string}}. rate намеренно не отправляется: для productId сервер берёт ставку из продукта. Срок UI кратен 12 месяцам, в запросе — годы. Пределы продукта проверяются перед отправкой и повторно backend.

Ответ: ApplicationResponse. Все четыре статуса поддержаны: UNDER_CONSIDERATION, ACCEPTED, REJECTED, COUNTER_OFFER. Исходные параметры и counterOffer разделены. Источник решений только application_server; frontend не обращается к внутреннему decision callback и не хранит заявки в localStorage.

Важные замечания команде:
- Нет eligibility metadata в ProductGet. Возраст/залог/ООО/ИП не являются доступными фильтрами API.
- JWT-секреты и пароли БД в архиве заданы development-конфигурацией. Не переносить их во frontend; перед публичным запуском заменить серверные значения и использовать HTTPS.
- В user_server application.properties стоит ddl-auto=updatespring.application.name=demo — проверить и исправить на допустимое значение update перед запуском (в предоставленном архиве строка склеена).
- При недоступности decision_service заявка остаётся UNDER_CONSIDERATION. Обновление страницы frontend лишь читает статус, не запускает серверный retry.
- API не заявляет идемпотентность POST заявок: повторять после timeout автоматически нельзя.
- Токены in-memory — сознательный выбор: нет длительного хранения Bearer в localStorage. Для постоянной сессии рекомендуется серверный BFF с HttpOnly cookie.

Старый openapi.yaml с /api/v1 не является контрактом этого backend и удалён. Актуальная спецификация должна генерироваться командой backend из контроллеров.
