package ru.cabinet.applications.dto;

import jakarta.validation.constraints.*;
import ru.cabinet.applications.data.OrganizationType;

import java.math.BigDecimal;

/**
 * Данные калькулятора на сайте. Используются и при выборе готового продукта (для проверки лимитов),
 * и при подаче без продукта (тогда rate обязательна).
 */
public record CalculatorRequest(
        /** ставка, % годовых (обязательна, если productId не передан) */
        @DecimalMin(value = "0.01") @Digits(integer = 3, fraction = 2) BigDecimal rate,

        @NotNull @DecimalMin(value = "1000") BigDecimal amount,

        @NotNull @Min(1) @Max(30) Integer durationYears,

        @NotNull OrganizationType organizationType,

        @NotNull Boolean collateral,

        @NotBlank @Size(max = 500) String purpose
) {}
