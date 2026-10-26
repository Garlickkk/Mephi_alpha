package ru.cabinet.applications.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import ru.cabinet.applications.client.DecisionOutcome;
import ru.cabinet.applications.data.CounterOffer;

/** Callback от сервиса принятия решений, когда решение принято асинхронно */
public record DecisionCallbackRequest(
        @NotBlank String decisionId,
        @NotNull DecisionOutcome outcome,
        String comment,
        @Valid CounterOffer counterOffer
) {}
