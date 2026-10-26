package ru.cabinet.applications.data;

import java.math.BigDecimal;

/** Компромиссные условия, предложенные банком */
public record CounterOffer(
        BigDecimal rate,
        BigDecimal amount,
        Integer durationYears
) {}
