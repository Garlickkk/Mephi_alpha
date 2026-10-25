package ru.cabinet.applications.dto;

import ru.cabinet.applications.data.ApplicationStatus;
import ru.cabinet.applications.data.CounterOffer;
import ru.cabinet.applications.data.CreditApplication;
import ru.cabinet.applications.data.OrganizationType;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Заявка для клиента. Если status = ACCEPTED и counterOffer != null,
 * клиент принял компромиссные условия: итоговые условия = counterOffer.
 */
public record ApplicationResponse(
        Long id,
        ApplicationStatus status,
        OrganizationType organizationType,
        Long productId,
        String productTitle,
        BigDecimal productInterest,
        BigDecimal rate,
        BigDecimal amount,
        int durationYears,
        String purpose,
        boolean collateral,
        String decisionComment,
        CounterOffer counterOffer,
        Instant createdAt,
        Instant updatedAt
) {
    public static ApplicationResponse from(CreditApplication a) {
        return new ApplicationResponse(
                a.getId(),
                a.getStatus(),
                a.getOrganizationType(),
                a.getProductId(),
                a.getProductTitle(),
                a.getProductInterest(),
                a.getRate(),
                a.getAmount(),
                a.getDurationYears(),
                a.getPurpose(),
                a.isCollateral(),
                a.getDecisionComment(),
                a.getCounterOffer(),
                a.getCreatedAt(),
                a.getUpdatedAt()
        );
    }
}
