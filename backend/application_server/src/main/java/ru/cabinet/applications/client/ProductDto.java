package ru.cabinet.applications.client;

import java.util.Set;

/** Ответ product_server GET /products/{id} (формат ProductGet) */
public record ProductDto(
        Long id,
        String title,
        String purposes,
        Double interest,
        Double discountInterest,
        String discountConditions,
        Integer minSum,
        Integer maxSum,
        Integer minDurationYear,
        Integer maxDurationYear,
        Set<String> repaymentTypes,
        String mainDifference
) {}
