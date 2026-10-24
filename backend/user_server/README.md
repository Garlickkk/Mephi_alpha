Сервис пользователей (организаций-клиентов личного кабинета): регистрация, аутентификация по JWT (access + refresh), хранение данных в PostgreSQL.

## Стек

- Java 21
- Kotlin 2.3.21
- Spring Boot 4.1.2 (Web MVC, Data JPA, Security)
- PostgreSQL (драйвер `org.postgresql:postgresql`)
- JJWT 0.13.0 для подписи и разбора токенов (HS256)
- BCrypt для хранения паролей

## Структура

```
src/main/kotlin/ru/cabinet/user/
├── Application.kt                 точка входа
├── controllers/
│   ├── AuthController.kt          /api/v0/auth/**
│   └── UserController.kt          /api/v0/users/**
├── auth/
│   ├── config/SecurityConfig.kt   правила доступа, CORS, BCrypt
│   ├── jwt/                       выпуск и проверка токенов, фильтр JWT
│   └── users/                     UserDetails, роли, загрузка пользователя
└── data/
    ├── models/                    сущность UserEntity, DTO, перечисления
    ├── repositories/              UserRepository (Spring Data JPA)
    └── services/                  AuthService, UserService
```

## Модель пользователя

Сущность `UserEntity` (таблица `users`):

| Поле | Описание |
|------|----------|
| `login` | логин, используется как subject в JWT |
| `password` | хэш BCrypt |
| `firstName`, `lastName`, `secondName` | ФИО |
| `organizationType` | `OOO`, `IP` или `AO` |
| `inn` | ИНН, уникальный |
| `ogrn` | ОГРН, уникальный |
| `registrationDate` | дата регистрации (ISO `yyyy-MM-dd`) |
| `okved` | основной ОКВЭД |
| `roles` | список ролей |
| `refreshToken`, `refreshTokenExpire` | текущий refresh-токен и срок его действия |

## API

Базовый путь: `/api/v0`.

### Аутентификация (`/auth`, доступно без токена)

| Метод | Путь | Тело запроса | Ответ |
|-------|------|--------------|-------|
| POST | `/auth/register` | `RegisterRequest` | `201` + `TokenResponse` |
| POST | `/auth/login` | `{ "login", "password" }` | `200` + `TokenResponse` |
| POST | `/auth/refresh` | `{ "refreshToken" }` | `200` + `TokenResponse` (с ротацией refresh) |
| POST | `/auth/logout` | — (нужен `Authorization: Bearer <access>`) | `204` |

`RegisterRequest`: `login`, `password` (минимум 8 символов), `firstName`, `lastName`, `secondName`, `organizationType`, `inn`, `ogrn`, `registrationDate`, `okved`.

`TokenResponse`: `accessToken`, `refreshToken`, `tokenType` (всегда `Bearer`), `expiresIn` (секунды, для access).

Пример регистрации:

```bash
curl -X POST http://localhost:8082/api/v0/auth/register \
  -H "Content-Type: application/json" \
  -d '{
        "login": "ooo_romashka",
        "password": "secret123",
        "firstName": "Иван",
        "lastName": "Иванов",
        "secondName": "Иванович",
        "organizationType": "OOO",
        "inn": "7701234567",
        "ogrn": "1027700132195",
        "registrationDate": "2020-05-14",
        "okved": "62.01"
      }'
```

### Пользователи (`/users`, только роль ADMIN по правилам URL)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/users` | список всех пользователей |
| GET | `/users/{login}` | пользователь по логину |

Заголовок `Authorization: Bearer <access>` обязателен для всех запросов, кроме `/auth/**`.

## Токены

- **Access** — подписан HS256, содержит `sub` (login), `inn`, `organization_type`, `okved_main`, `registration_date`, `authorities`. Проверяется без обращения к БД (но фильтр загружает пользователя из БД на каждый запрос).
- **Refresh** — содержит `type=refresh`, хранится в таблице `users`. При обновлении выдаётся новая пара, старый refresh перестаёт действовать.
- **Logout** отзывает refresh-токен в БД. Access-токен остаётся действительным до истечения срока.

Значения сроков задаются в `application.properties` в миллисекундах (`test.access-token-expiration`, `test.refresh-token-expiration`).

## Конфигурация

Файл `src/main/resources/application.properties`:

| Ключ | Значение по умолчанию | Комментарий |
|------|----------------------|-------------|
| `server.port` | `8082` | порт сервиса |
| `spring.datasource.url` | `jdbc:postgresql://localhost:5433/users` | база данных |
| `spring.datasource.username` / `password` | `user` / `user_pass` | учётные данные БД |
| `test.secret.key` | — | секрет для подписи JWT, **заменить и вынести из репозитория** |
| `test.access-token-expiration` | `2592000000` | 30 дней |
| `test.refresh-token-expiration` | `3600000` | 1 час |
| `spring.jpa.hibernate.ddl-auto` | `update` | схема создаётся автоматически |

Секрет лучше передавать через переменную окружения, например:

```properties
test.secret.key=${JWT_SECRET}
spring.datasource.password=${DB_PASSWORD}
```

CORS разрешён для `http://localhost:3000`, `http://localhost:5173`, `http://localhost:8080`.

## Запуск

Нужны Java 21 и PostgreSQL, доступный на `localhost:5433` с базой `users`.

Поднять PostgreSQL в Docker:

```bash
docker run -d --name users-db -p 5433:5432 \
  -e POSTGRES_DB=users \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=user_pass \
  postgres:16
```

Запустить сервис:

```bash
./mvnw spring-boot:run
```

Сборка и тесты:

```bash
./mvnw clean package
./mvnw test
```

Тест `ApplicationTests` поднимает весь контекст и требует работающую БД.

## Известные ограничения

- Секреты (JWT и пароль БД) лежат в `application.properties` в открытом виде.
- Срок жизни refresh-токена меньше срока жизни access-токена: ключи, по-видимому, перепутаны.
- Роли `ADMIN` не существует в `SecurityRole`, поэтому эндпоинты `/users` недоступны никому.
- Эндпоинта `/users/me` нет, хотя правило безопасности для него задано.
- Аннотации `@PreAuthorize` не работают: не подключён `@EnableMethodSecurity`.
- Нет глобального обработчика ошибок: ошибки валидации (`require`/`IllegalArgumentException`) и вход с несуществующим логином возвращают 500, а не 400. Неверный пароль даёт 401.
- Схема БД управляется через `ddl-auto=update`, миграций нет.
- Подробный разбор — в отдельной оценке проекта.
