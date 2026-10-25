package ru.cabinet.applications.controller;

import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import ru.cabinet.applications.dto.ApplicationResponse;
import ru.cabinet.applications.dto.DecisionCallbackRequest;
import ru.cabinet.applications.exception.ApiException;
import ru.cabinet.applications.service.CreditApplicationService;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Внутренний эндпоинт: вызывается только сервисом принятия решений, не должен быть доступен клиенту через фронтенд */
@RestController
@RequestMapping("/api/v0/internal/applications")
public class DecisionCallbackController {

    private final CreditApplicationService service;
    private final String internalToken;

    public DecisionCallbackController(CreditApplicationService service,
                                      @Value("${app.services.internal-token}") String internalToken) {
        this.service = service;
        this.internalToken = internalToken;
    }

    @PostMapping("/{id}/decision")
    public ApplicationResponse decisionCallback(@PathVariable long id,
                                                @RequestHeader(value = "X-Service-Token", required = false) String token,
                                                @Valid @RequestBody DecisionCallbackRequest request) {
        if (token == null || !MessageDigest.isEqual(
                token.getBytes(StandardCharsets.UTF_8),
                internalToken.getBytes(StandardCharsets.UTF_8))) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Неверный сервисный токен");
        }
        return service.applyDecisionCallback(id, request);
    }
}
