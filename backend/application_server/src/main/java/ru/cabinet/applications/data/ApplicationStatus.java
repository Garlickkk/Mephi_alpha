package ru.cabinet.applications.data;

public enum ApplicationStatus {
    /** Заявка на рассмотрении */
    UNDER_CONSIDERATION,
    /** Заявка принята (банк одобрил, либо клиент принял компромиссные условия) */
    ACCEPTED,
    /** Заявка отклонена (банк отказал, либо клиент отклонил компромиссные условия) */
    REJECTED,
    /** Банк предложил компромиссные условия, ожидается ответ клиента */
    COUNTER_OFFER
}
