package ru.cabinet.applications.data;

import java.math.BigDecimal;

/** Снимок продукта на момент подачи заявки */
public record ProductRef(
        Long id,
        String title,
        BigDecimal interest
) {}
