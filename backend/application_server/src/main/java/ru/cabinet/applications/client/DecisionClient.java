package ru.cabinet.applications.client;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class DecisionClient {

    private final RestClient restClient;

    public DecisionClient(@Qualifier("decisionRestClient") RestClient restClient) {
        this.restClient = restClient;
    }

    /**
     * Отправляет заявку на рассмотрение. Бросает RestClientException, если сервис недоступен или отвечает ошибкой:
     * в этом случае заявка остаётся в статусе UNDER_CONSIDERATION и уходит на повторную отправку.
     */
    public DecisionResponse submit(DecisionRequest request) {
        return restClient.post()
                .uri("/api/v1/decisions")
                .header("Idempotency-Key", String.valueOf(request.applicationId()))
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(DecisionResponse.class);
    }
}
