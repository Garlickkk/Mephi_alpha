package ru.cabinet.applications.client;

import ru.cabinet.applications.data.CounterOffer;

import java.math.BigDecimal;

/** Ответ POST /api/v1/decisions. Скоринговые метрики опциональны для обратной совместимости. */
public record DecisionResponse(
        String decisionId,
        DecisionOutcome outcome,
        String comment,
        CounterOffer counterOffer,
        Integer score,
        String riskGrade,
        BigDecimal interestRate,
        BigDecimal monthlyPayment,
        BigDecimal dtiRatio,
        BigDecimal profitabilityMargin
) {}
