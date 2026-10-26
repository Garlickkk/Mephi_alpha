# Архитектура, процесс и модель данных

## Границы MVP

Клиенту нужны подбор суммы/срока, однократный ввод реквизитов, прозрачный статус и возможность ответить на встречное предложение. Банку нужны проверка параметров, оценка риска и обработка пограничных случаев. Это продуктовые предположения по кейсу, не результаты проведённых интервью.

В MVP включены регистрация, каталог, заявка, обогащение синтетическими финансовыми показателями, балльная модель и ручное решение через API. Подписание, выдача денег, документы, новости и отдельный интерфейс сотрудника не реализованы. Скоринг отделён от решения: балл задаёт рейтинг и предельную долговую нагрузку; условия продукта и стоп-факторы могут изменить исход.

## Архитектурная схема

```mermaid
flowchart LR
    Client[Браузер клиента] --> Web[Frontend + Nginx :8085]
    Web --> User[user_server :8082]
    Web --> Product[product_server :8081]
    Web --> Application[application_server :8083]
    User --> Users[(PostgreSQL users)]
    Product --> Products[(PostgreSQL products)]
    Application --> Applications[(PostgreSQL applications)]
    Application -->|GET /products/id| Product
    Application -->|POST /api/v1/decisions| Decision[decision_service :8090]
    Decision --> Mocks[Локальные синтетические БКИ и финансы]
    Reviewer[Сотрудник: Swagger / коллекция] -->|X-Service-Token, /resolve| Decision
    Decision -->|callback итогового решения| Application
```

Клиентские запросы идут через один origin, без CORS между браузером и сервисами. JWT выдаётся user_server и проверяется application_server общим ключом. Внутренний callback не проксируется frontend. В Compose БД и Java API не публикуются на хост, Swagger скоринга доступен только на localhost. Сотрудник в MVP использует общий сервисный токен; персонального RBAC для сотрудников нет.

## Сквозной процесс

```mermaid
sequenceDiagram
    actor C as Клиент
    participant U as user_server
    participant A as application_server
    participant P as product_server
    participant D as decision_service
    C->>U: Регистрация / вход
    U-->>C: accessToken + refreshToken
    C->>P: Каталог через proxy
    C->>A: POST application + Bearer
    A->>P: Проверка продукта и лимитов
    A->>A: Сохранить UNDER_CONSIDERATION
    A->>D: Заявка, claims клиента, продукт
    D->>D: Локальные моки, стоп-факторы, балл, DTI
    D-->>A: APPROVED / REJECTED / COUNTER_OFFER / PENDING
    A-->>C: Сохранённая заявка и текущий статус
    opt Ручная проверка
        D->>A: Callback после /resolve
    end
    C->>A: Получить статус / ответить на counter-offer
```

## Диаграмма состояний заявки

```mermaid
stateDiagram-v2
    [*] --> UNDER_CONSIDERATION: Заявка сохранена
    UNDER_CONSIDERATION --> ACCEPTED: APPROVED
    UNDER_CONSIDERATION --> REJECTED: REJECTED
    UNDER_CONSIDERATION --> COUNTER_OFFER: COUNTER_OFFER
    UNDER_CONSIDERATION --> UNDER_CONSIDERATION: PENDING / сервис недоступен
    COUNTER_OFFER --> ACCEPTED: Клиент принял условия
    COUNTER_OFFER --> REJECTED: Клиент отклонил условия
    ACCEPTED --> [*]
    REJECTED --> [*]
```

`APPROVED` в сервисе решений соответствует `ACCEPTED` в заявке. `PENDING` не отдельный клиентский статус, он оставляет `UNDER_CONSIDERATION`. Решение сотрудника приходит тем же callback. Повтор callback с тем же decisionId после итогового решения возвращает текущее состояние; ответ на уже обработанное встречное предложение даёт 409. У частичного `counterOffer` поля `null` означают сохранение исходных условий.

Отдельные состояния decision_service: `DECIDED` (автоматическое решение), `PENDING` (очередь), `RESOLVED` (решение сотрудника). Доставка callback фиксируется отдельно: `IN_PROGRESS`, `DELIVERED`, `FAILED`.

## Модель данных

```mermaid
erDiagram
    USERS {
        bigint id PK
        string login
        string password "BCrypt"
        string inn UK
        string ogrn UK
        string organization_type
        date registration_date
        string okved
        string roles
        string refresh_token
        datetime refresh_expire
    }
    PRODUCTS {
        bigint id PK
        string title UK
        double interest
        double discount_interest
        int min_sum
        int max_sum
        int min_duration
        int max_duration
    }
    PRODUCT_REPAYMENT_TYPES {
        bigint product_id FK
        string repayment_type
    }
    CREDIT_APPLICATIONS {
        bigint id PK
        bigint version "optimistic locking"
        string client_login "логическая связь"
        string client_inn "снимок"
        bigint product_id "логическая связь"
        decimal amount
        decimal rate
        int duration_years
        string status
        string decision_id
        string decision_comment
        decimal counter_amount
        decimal counter_rate
        int counter_duration_years
        int scoring_score
        string risk_grade
        datetime created_at
        datetime updated_at
    }
    USERS ||--o{ CREDIT_APPLICATIONS : "по client_login, без FK между БД"
    PRODUCTS ||--o{ CREDIT_APPLICATIONS : "снимок продукта, без FK между БД"
    PRODUCTS ||--o{ PRODUCT_REPAYMENT_TYPES : "FK внутри products"
```

Дополнительно у пользователя сохраняется ФИО; у продукта — цели, условия скидки и описание; у заявки — цель, залог, тип организации, снимок названия/ставки продукта и метрики платежа, DTI, рентабельности. Полные поля: DTO и [OpenAPI](openapi.json). Денежные поля заявки — BigDecimal/NUMERIC; вычисления скоринга используют float.

`StoredDecision` хранится в памяти Python: decisionId, applicationId, fingerprint запроса, response, recommendation, статус, причина ручной проверки, resolvedBy, callbackStatus и даты. Это не четвёртая БД. Повтор запроса скоринга требует `Idempotency-Key = applicationId`; POST клиентской заявки идемпотентности не имеет.

## Ограничения надёжности и безопасности

- Очередь и идемпотентность скоринга теряются при перезапуске; несколько реплик decision_service не имеют общего состояния.
- При недоступности скоринга заявка сохраняется, но планировщика повторной отправки нет. Кнопка обновления статуса повторно скоринг не запускает.
- Callback имеет до пяти попыток при сетевой ошибке/5xx; после исчерпания требуется вмешательство.
- PostgreSQL сохраняется в томах; схемой Java управляет `ddl-auto=update`, версионируемых миграций нет.
- В исходных properties есть демонстрационные секреты; Compose переопределяет их. Logout отзывает refresh, access остаётся действителен до истечения.
- Персональный доступ сотрудника, TLS, аудит действий и промышленная эксплуатация не реализованы. Собственные Java healthcheck проверяют TCP-порт; это не полная проверка бизнес-функций.
