package ru.cabinet.applications.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record CreateApplicationRequest(
        /** id готового продукта из product_server; если null, заявка подаётся по данным калькулятора */
        @Positive Long productId,

        @NotNull @Valid CalculatorRequest calculator
) {}
