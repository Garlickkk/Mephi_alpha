package ru.cabinet.applications.security;

import ru.cabinet.applications.data.OrganizationType;

import java.time.LocalDate;

/** Данные клиента, извлечённые из access-токена (JWT, выпускается user_server) */
public record ClientPrincipal(
        String login,
        String inn,
        OrganizationType organizationType,
        String okvedMain,
        LocalDate registrationDate
) {}
