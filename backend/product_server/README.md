# Product Server

Сервис на Kotlin + Spring Boot (Spring Web MVC, Spring Data JPA), который отдаёт каталог кредитных продуктов из PostgreSQL.

- Java 21, Kotlin 2.3.21, Spring Boot 4.1.2
- Порт приложения: `8081`
- База данных: PostgreSQL (запускается в Docker)
- Порт докера 5432 (по умолчанию)
---

## Содержание

1. [API](#api)
2. [Модель данных](#модель-данных)
3. [Запуск PostgreSQL в Docker](#запуск-postgresql-в-docker)
4. [Подключение приложения к БД](#подключение-приложения-к-бд)
5. [Запуск приложения](#запуск-приложения)
6. [Проверка](#проверка)

---

## API

Базовый URL: `http://localhost:8081`

### GET /products

Возвращает список всех продуктов.

**Ответ `200 OK`:**

```json
{
  "products": [
    {
      "id": 1,
      "title": "Потребительский кредит",
      "purposes": "Покупка товаров и услуг",
      "interest": 12.5,
      "discountInterest": 10.5,
      "discountConditions": "при оформлении страховки",
      "minSum": 50000,
      "maxSum": 3000000,
      "minDurationYear": 1,
      "maxDurationYear": 5,
      "repaymentTypes": ["EQUAL_TOTAL_PARTS", "EQUAL_PRINCIPAL_PARTS"],
      "mainDifference": "Без залога и поручителей"
    }
  ]
}
```

Если продуктов нет, возвращается `{"products": []}`.

### GET /products/{id}

Возвращает один продукт по его идентификатору.

| Параметр | Расположение | Тип  | Обязательный | Описание               |
|----------|--------------|------|--------------|------------------------|
| `id`     | path         | Long | да           | Идентификатор продукта |

**Ответ `200 OK`:** объект продукта в том же формате, что и элемент массива `products` выше.

**Ответ `404 Not Found`**, если продукта с таким `id` нет:

```json
{
  "message": "Product with id=42 not founded",
  "dateTime": "2026-10-23T14:30:00"
}
```

**Ответ `500 Internal Server Error`** при любой другой необработанной ошибке. Тело имеет тот же формат, что и при 404, а `message` содержит текст исключения.

### Поля продукта

| Поле                 | Тип             | Описание                                  |
|----------------------|-----------------|-------------------------------------------|
| `id`                 | number          | Идентификатор                             |
| `title`              | string          | Название, уникальное                      |
| `purposes`           | string          | Цели кредита                              |
| `interest`           | number (double) | Базовая процентная ставка                 |
| `discountInterest`   | number (double) | Ставка со скидкой (не больше базовой)     |
| `discountConditions` | string \| null  | Условия получения скидки                  |
| `minSum`             | number (int)    | Минимальная сумма кредита                 |
| `maxSum`             | number (int)    | Максимальная сумма кредита                |
| `minDurationYear`    | number (int)    | Минимальный срок, в годах                 |
| `maxDurationYear`    | number (int)    | Максимальный срок, в годах                |
| `repaymentTypes`     | array of enum   | Способы погашения (см. ниже)              |
| `mainDifference`     | string          | Главное отличие продукта                  |

Допустимые значения `repaymentTypes`:

- `EQUAL_PRINCIPAL_PARTS`: равными частями по основному долгу (платёж с каждым месяцем уменьшается)
- `EQUAL_TOTAL_PARTS`: равными частями по сумме кредита (аннуитет, платёж одинаковый)

### Примеры запросов

```bash
curl -i http://localhost:8081/products
curl -i http://localhost:8081/products/1
```

> В проекте также есть DTO `ProductPost` и `ProductPut`, но соответствующие эндпоинты (`POST`, `PUT`) в контроллере пока не реализованы.

---

## Модель данных

Таблицы создаёт Hibernate по сущности `Product`.

**Таблица `products`**

| Колонка               | Тип              | Ограничения                                 |
|-----------------------|------------------|---------------------------------------------|
| `id`                  | BIGINT           | PRIMARY KEY, IDENTITY                       |
| `title`               | VARCHAR(100)     | NOT NULL, UNIQUE                            |
| `purposes`            | TEXT             | NOT NULL                                    |
| `interest`            | DOUBLE PRECISION | NOT NULL, > 0                               |
| `discount_interest`   | DOUBLE PRECISION | NOT NULL, > 0 и ≤ `interest`                |
| `discount_conditions` | TEXT             | NULL                                        |
| `min_sum`             | INTEGER          | NOT NULL, ≥ 0                               |
| `max_sum`             | INTEGER          | NOT NULL, > `min_sum`                       |
| `min_duration`        | INTEGER          | NOT NULL, ≥ 0                               |
| `max_duration`        | INTEGER          | NOT NULL, > `min_duration`                  |
| `main_difference`     | TEXT             | NOT NULL                                    |

**Таблица `product_repayment_types`** (коллекция способов погашения)

| Колонка          | Тип     | Описание                                         |
|------------------|---------|--------------------------------------------------|
| `product_id`     | BIGINT  | Ссылка на `products.id`                          |
| `repayment_type` | VARCHAR | `EQUAL_PRINCIPAL_PARTS` или `EQUAL_TOTAL_PARTS`  |

Ограничения из `init`-блока сущности (например, `maxSum > minSum`) проверяются приложением при создании объекта `Product`, а не на уровне БД.

---

## Запуск PostgreSQL в Docker

### Требования

- Установленный Docker (Docker Desktop на Windows/macOS или Docker Engine на Linux)

### 1. Запуск контейнера

```bash
docker run -d \
  --name product-postgres \
  -e POSTGRES_USER=product_user \
  -e POSTGRES_PASSWORD=product_pass \
  -e POSTGRES_DB=products \
  -p 5432:5432 \
  -v product_pgdata:/var/lib/postgresql/data \
  postgres:16
```

Что здесь происходит:

- `--name product-postgres`: имя контейнера, по которому к нему можно обращаться
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: пользователь, пароль и база, которые создаются при первом запуске
- `-p 5432:5432`: пробрасывает порт PostgreSQL на localhost
- `-v product_pgdata:/var/lib/postgresql/data`: именованный том, данные сохраняются после остановки и удаления контейнера

### 2. Проверка, что база поднялась

```bash
docker ps --filter name=product-postgres
docker logs product-postgres
```

В логах должна появиться строка `database system is ready to accept connections`.

### 3. Подключение к базе через psql (опционально)

```bash
docker exec -it product-postgres psql -U product_user -d products
```

Выход из `psql`: команда `\q`.

### Остановка и удаление

```bash
docker stop product-postgres      # остановить, данные сохранятся
docker start product-postgres     # снова запустить
docker rm -f product-postgres     # удалить контейнер (том с данными останется)
docker volume rm product_pgdata   # удалить данные полностью
```

### Альтернатива: docker-compose.yml

Если удобнее управлять через compose, создайте файл `docker-compose.yml` в корне проекта:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: product-postgres
    environment:
      POSTGRES_USER: product_user
      POSTGRES_PASSWORD: product_pass
      POSTGRES_DB: products
    ports:
      - "5432:5432"
    volumes:
      - product_pgdata:/var/lib/postgresql/data

volumes:
  product_pgdata:
```

Запуск: `docker compose up -d`, остановка: `docker compose down`.

---

## Подключение приложения к БД

В `src/main/resources/application.properties` сейчас нет настроек источника данных, поэтому приложение нужно подключить к базе. Самый простой способ — переменные окружения. Spring Boot читает их автоматически, код менять не нужно:

| Переменная окружения            | Значение                                      |
|---------------------------------|-----------------------------------------------|
| `SPRING_DATASOURCE_URL`         | `jdbc:postgresql://localhost:5432/products`   |
| `SPRING_DATASOURCE_USERNAME`    | `product_user`                                |
| `SPRING_DATASOURCE_PASSWORD`    | `product_pass`                                |
| `SPRING_JPA_HIBERNATE_DDL_AUTO` | `update` (создаст таблицы при первом запуске) |

Либо можно прописать то же самое в `application.properties`:

```properties
spring.application.name=demo
server.port=8081

spring.datasource.url=jdbc:postgresql://localhost:5432/products
spring.datasource.username=product_user
spring.datasource.password=product_pass

spring.jpa.hibernate.ddl-auto=update
spring.jpa.open-in-view=false
```

> Для продакшена пароль лучше не хранить в файле: используйте переменные окружения или секреты. Также после первого создания схемы рекомендуется заменить `update` на `validate` или `none`.

---

## Запуск приложения

Требования: JDK 21. Maven отдельно ставить не нужно, в проекте есть Maven Wrapper.

Из корня проекта:

```bash
# Linux / macOS
./mvnw spring-boot:run

# Windows
mvnw.cmd spring-boot:run
```

С переменными окружения в одной команде:

```bash
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/products \
SPRING_DATASOURCE_USERNAME=product_user \
SPRING_DATASOURCE_PASSWORD=product_pass \
SPRING_JPA_HIBERNATE_DDL_AUTO=update \
./mvnw spring-boot:run
```

Сборка jar-файла и запуск:

```bash
./mvnw clean package
java -jar target/demo-0.0.1-SNAPSHOT.jar
```

---

## Проверка

### Добавление тестовых данных

Таблицы создаются Hibernate при первом запуске, но продуктов в них нет. Чтобы проверить API, добавьте запись. Выполнить SQL можно через `psql` внутри контейнера:

```bash
docker exec -it product-postgres psql -U product_user -d products
```
Перейти в БД из терминала (контейнер должен быть запущенным)
```bash
docker exec -it product-postgres psql -U product_user -d products
```
Тестовые данные:
```sql
INSERT INTO products (title, purposes, interest, discount_interest, discount_conditions,
                      min_sum, max_sum, min_duration, max_duration, main_difference)
VALUES ('Потребительский кредит', 'Покупка товаров и услуг', 12.5, 10.5,
        'при оформлении страховки', 50000, 3000000, 1, 5, 'Без залога и поручителей');

INSERT INTO product_repayment_types (product_id, repayment_type)
VALUES (1, 'EQUAL_TOTAL_PARTS'), (1, 'EQUAL_PRINCIPAL_PARTS');
```

### Запросы

```bash
curl -i http://localhost:8081/products
curl -i http://localhost:8081/products/1
curl -i http://localhost:8081/products/999   # ожидается 404
```

---

## Структура проекта

```
src/main/kotlin/ru/cabinet/prodects/
├── Application.kt
├── controllers/
│   ├── ProductController.kt                  # REST-эндпоинты
│   └── exception/GlobalExceptionHandler.kt   # обработка ошибок (404, 500)
└── data/
    ├── ProductService.kt                     # логика и маппинг Product -> ProductGet
    ├── dto/                                  # ProductGet, ProductPost, ProductPut, ProductGetContainer, ApiResponse
    ├── models/                               # Product (JPA-сущность), TypeOfRepayment, ProductNotFoundedException
    └── repositories/ProductRepository.kt
```