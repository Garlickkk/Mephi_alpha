package ru.cabinet.applications.client;

import ru.cabinet.applications.data.OrganizationType;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

/** Тело запроса POST /api/v1/decisions в сервис принятия решений */
public record DecisionRequest(
        Long applicationId,
        ClientInfo client,
        LoanInfo loan,
        ProductDto product,
        Instant requestedAt
) {
    public record ClientInfo(
            String inn,
            OrganizationType organizationType,
            String okvedMain,
            LocalDate registrationDate
    ) {}

    public record LoanInfo(
            BigDecimal rate,
            BigDecimal amount,
            int durationYears,
            String purpose,
            boolean collateral
    ) {}
}
