package ru.cabinet.applications.dto;

import jakarta.validation.constraints.NotNull;

public record CounterOfferDecisionRequest(
        /** true: принять компромиссные условия, false: отклонить */
        @NotNull Boolean accept
) {}
