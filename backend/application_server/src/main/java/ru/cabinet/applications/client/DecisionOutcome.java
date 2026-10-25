package ru.cabinet.applications.client;

/** Результат из сервиса принятия решений (словарь decision-сервиса, см. docs/decision-service-api.md) */
public enum DecisionOutcome {
    APPROVED,
    REJECTED,
    COUNTER_OFFER,
    /** Решение ещё не принято (ручная проверка), придёт callback'ом */
    PENDING
}
