package ru.cabinet.applications.client;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import ru.cabinet.applications.exception.ApiException;

@Component
public class ProductClient {

    private final RestClient restClient;

    public ProductClient(@Qualifier("productRestClient") RestClient restClient) {
        this.restClient = restClient;
    }

    public ProductDto getProduct(long id) {
        try {
            ProductDto product = restClient.get()
                    .uri("/products/{id}", id)
                    .retrieve()
                    .onStatus(status -> status.value() == HttpStatus.NOT_FOUND.value(), (request, response) -> {
                        throw new ApiException(HttpStatus.NOT_FOUND, "Продукт с id=" + id + " не найден");
                    })
                    .body(ProductDto.class);
            if (product == null) {
                throw new ApiException(HttpStatus.BAD_GATEWAY, "Пустой ответ сервиса продуктов");
            }
            return product;
        } catch (RestClientException e) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Сервис продуктов недоступен");
        }
    }
}
