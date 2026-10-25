package ru.cabinet.applications.data;

import java.math.BigDecimal;

/** Условия кредита, которые клиент запросил (из продукта или калькулятора) */
public record LoanTerms(
        BigDecimal rate,
        BigDecimal amount,
        int durationYears,
        String purpose,
        boolean collateral
) {}
