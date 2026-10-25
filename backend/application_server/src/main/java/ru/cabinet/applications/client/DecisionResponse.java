package ru.cabinet.applications.client;

import ru.cabinet.applications.data.CounterOffer;

/** Ответ POST /api/v1/decisions */
public record DecisionResponse(
        String decisionId,
        DecisionOutcome outcome,
        String comment,
        CounterOffer counterOffer
) {}
