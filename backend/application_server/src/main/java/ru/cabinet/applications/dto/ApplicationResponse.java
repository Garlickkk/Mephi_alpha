package ru.cabinet.applications.dto;

import ru.cabinet.applications.data.ApplicationStatus;
import ru.cabinet.applications.data.CounterOffer;
import ru.cabinet.applications.data.CreditApplication;
import ru.cabinet.applications.data.OrganizationType;

import java.math.BigDecimal;
import java.time.Instant;

/** Клиентское представление заявки, включая объяснимые метрики скоринга. */
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
        Integer scoringScore,
        String riskGrade,
        BigDecimal scoringInterestRate,
        BigDecimal scoringMonthlyPayment,
        BigDecimal dtiRatio,
        BigDecimal profitabilityMargin,
        Instant createdAt,
        Instant updatedAt
) {
    public static ApplicationResponse from(CreditApplication a) {
        return new ApplicationResponse(
                a.getId(), a.getStatus(), a.getOrganizationType(), a.getProductId(), a.getProductTitle(),
                a.getProductInterest(), a.getRate(), a.getAmount(), a.getDurationYears(), a.getPurpose(),
                a.isCollateral(), a.getDecisionComment(), a.getCounterOffer(), a.getScoringScore(),
                a.getRiskGrade(), a.getScoringInterestRate(), a.getScoringMonthlyPayment(), a.getDtiRatio(),
                a.getProfitabilityMargin(), a.getCreatedAt(), a.getUpdatedAt()
        );
    }
}
