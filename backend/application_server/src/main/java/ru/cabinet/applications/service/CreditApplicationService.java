package ru.cabinet.applications.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;
import ru.cabinet.applications.client.DecisionClient;
import ru.cabinet.applications.client.DecisionOutcome;
import ru.cabinet.applications.client.DecisionRequest;
import ru.cabinet.applications.client.DecisionResponse;
import ru.cabinet.applications.client.ProductClient;
import ru.cabinet.applications.client.ProductDto;
import ru.cabinet.applications.data.ApplicationStatus;
import ru.cabinet.applications.data.CreditApplication;
import ru.cabinet.applications.data.CreditApplicationRepository;
import ru.cabinet.applications.data.LoanTerms;
import ru.cabinet.applications.data.ProductRef;
import ru.cabinet.applications.dto.ApplicationResponse;
import ru.cabinet.applications.dto.CalculatorRequest;
import ru.cabinet.applications.dto.CreateApplicationRequest;
import ru.cabinet.applications.dto.DecisionCallbackRequest;
import ru.cabinet.applications.exception.ApiException;
import ru.cabinet.applications.security.ClientPrincipal;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

@Service
public class CreditApplicationService {

    private static final Logger log = LoggerFactory.getLogger(CreditApplicationService.class);

    private final CreditApplicationRepository repository;
    private final ProductClient productClient;
    private final DecisionClient decisionClient;

    public CreditApplicationService(CreditApplicationRepository repository,
                                    ProductClient productClient,
                                    DecisionClient decisionClient) {
        this.repository = repository;
        this.productClient = productClient;
        this.decisionClient = decisionClient;
    }

    /** Подача заявки: сохраняем, отправляем на рассмотрение, возвращаем текущий статус */
    public ApplicationResponse submit(ClientPrincipal client, CreateApplicationRequest request) {
        CalculatorRequest calc = request.calculator();

        if (calc.organizationType() != client.organizationType()) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Тип организации в калькуляторе не совпадает с типом организации из учётной записи");
        }

        ProductDto product = null;
        BigDecimal rate;
        if (request.productId() != null) {
            product = productClient.getProduct(request.productId());
            checkProductLimits(product, calc);
            // при выборе готового продукта ставка берётся из продукта
            rate = BigDecimal.valueOf(product.interest());
        } else {
            if (calc.rate() == null) {
                throw new ApiException(HttpStatus.BAD_REQUEST,
                        "Для заявки без продукта нужно указать ставку калькулятора (rate)");
            }
            rate = calc.rate();
        }

        LoanTerms terms = new LoanTerms(
                rate,
                calc.amount(),
                calc.durationYears(),
                calc.purpose(),
                Boolean.TRUE.equals(calc.collateral())
        );
        ProductRef productRef = product == null
                ? null
                : new ProductRef(product.id(), product.title(), BigDecimal.valueOf(product.interest()));

        CreditApplication application = repository.save(CreditApplication.create(client, terms, productRef));
        application = sendForDecision(application, client, product);
        return ApplicationResponse.from(application);
    }

    @Transactional(readOnly = true)
    public ApplicationResponse getOwned(ClientPrincipal client, long id) {
        return ApplicationResponse.from(findOwned(client, id));
    }

    @Transactional(readOnly = true)
    public List<ApplicationResponse> listOwned(ClientPrincipal client, ApplicationStatus status) {
        List<CreditApplication> applications = status == null
                ? repository.findAllByClientLoginOrderByCreatedAtDesc(client.login())
                : repository.findAllByClientLoginAndStatusOrderByCreatedAtDesc(client.login(), status);
        return applications.stream().map(ApplicationResponse::from).toList();
    }

    /** Клиент принимает или отклоняет компромиссные условия */
    @Transactional
    public ApplicationResponse respondToCounterOffer(ClientPrincipal client, long id, boolean accept) {
        CreditApplication application = findOwned(client, id);
        application.respondToCounterOffer(accept);
        return ApplicationResponse.from(repository.save(application));
    }

    /** Callback от сервиса принятия решений (асинхронное решение) */
    @Transactional
    public ApplicationResponse applyDecisionCallback(long applicationId, DecisionCallbackRequest callback) {
        CreditApplication application = repository.findById(applicationId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND,
                        "Заявка с id=" + applicationId + " не найдена"));

        if (callback.outcome() == DecisionOutcome.PENDING) {
            return ApplicationResponse.from(application);
        }

        if (application.getStatus() != ApplicationStatus.UNDER_CONSIDERATION) {
            // повторный callback с тем же решением: идемпотентно возвращаем текущее состояние
            if (callback.decisionId().equals(application.getDecisionId())) {
                return ApplicationResponse.from(application);
            }
            throw new ApiException(HttpStatus.CONFLICT,
                    "Заявка уже имеет итоговый статус: " + application.getStatus());
        }

        application.applyDecision(
                callback.decisionId(),
                toStatus(callback.outcome()),
                callback.comment(),
                callback.counterOffer()
        );
        return ApplicationResponse.from(repository.save(application));
    }

    private CreditApplication findOwned(ClientPrincipal client, long id) {
        return repository.findByIdAndClientLogin(id, client.login())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Заявка с id=" + id + " не найдена"));
    }

    /**
     * Отправка в сервис принятия решений. Если сервис недоступен, заявка остаётся
     * в статусе UNDER_CONSIDERATION без decisionId и подлежит повторной отправке.
     */
    private CreditApplication sendForDecision(CreditApplication application, ClientPrincipal client, ProductDto product) {
        DecisionRequest request = new DecisionRequest(
                application.getId(),
                new DecisionRequest.ClientInfo(
                        client.inn(), client.organizationType(), client.okvedMain(), client.registrationDate()),
                new DecisionRequest.LoanInfo(
                        application.getRate(), application.getAmount(), application.getDurationYears(),
                        application.getPurpose(), application.isCollateral()),
                product,
                Instant.now()
        );

        try {
            DecisionResponse response = decisionClient.submit(request);
            if (response == null) {
                log.warn("Пустой ответ сервиса решений для заявки {}", application.getId());
                return application;
            }
            if (response.outcome() == DecisionOutcome.PENDING) {
                application.attachDecisionId(response.decisionId());
            } else {
                application.applyDecision(
                        response.decisionId(),
                        toStatus(response.outcome()),
                        response.comment(),
                        response.counterOffer()
                );
            }
            return repository.save(application);
        } catch (RestClientException | ApiException e) {
            log.warn("Заявка {} остаётся на рассмотрении, решение не получено: {}", application.getId(), e.getMessage());
            return application;
        }
    }

    private static void checkProductLimits(ProductDto product, CalculatorRequest calc) {
        if (calc.amount().compareTo(BigDecimal.valueOf(product.minSum())) < 0
                || calc.amount().compareTo(BigDecimal.valueOf(product.maxSum())) > 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Сумма должна быть от " + product.minSum() + " до " + product.maxSum() + " руб.");
        }
        if (calc.durationYears() < product.minDurationYear() || calc.durationYears() > product.maxDurationYear()) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Срок должен быть от " + product.minDurationYear() + " до " + product.maxDurationYear() + " лет");
        }
    }

    private static ApplicationStatus toStatus(DecisionOutcome outcome) {
        return switch (outcome) {
            case APPROVED -> ApplicationStatus.ACCEPTED;
            case REJECTED -> ApplicationStatus.REJECTED;
            case COUNTER_OFFER -> ApplicationStatus.COUNTER_OFFER;
            case PENDING -> ApplicationStatus.UNDER_CONSIDERATION;
        };
    }
}
