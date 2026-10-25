package ru.cabinet.applications.data;

import jakarta.persistence.*;
import org.springframework.http.HttpStatus;
import ru.cabinet.applications.exception.ApiException;
import ru.cabinet.applications.security.ClientPrincipal;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "credit_applications")
public class CreditApplication {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Оптимистическая блокировка: конкурентный callback и ответ клиента не перетрут друг друга */
    @Version
    private Long version;

    // --- клиент (берётся из JWT) ---
    @Column(name = "client_login", nullable = false)
    private String clientLogin;

    @Column(name = "client_inn", nullable = false)
    private String clientInn;

    @Enumerated(EnumType.STRING)
    @Column(name = "organization_type", nullable = false)
    private OrganizationType organizationType;

    // --- продукт (если выбран готовый) ---
    @Column(name = "product_id")
    private Long productId;

    @Column(name = "product_title")
    private String productTitle;

    @Column(name = "product_interest", precision = 6, scale = 2)
    private BigDecimal productInterest;

    // --- условия кредита ---
    @Column(name = "rate", nullable = false, precision = 6, scale = 2)
    private BigDecimal rate;

    @Column(name = "amount", nullable = false, precision = 15, scale = 2)
    private BigDecimal amount;

    @Column(name = "duration_years", nullable = false)
    private int durationYears;

    @Column(name = "purpose", nullable = false, columnDefinition = "TEXT")
    private String purpose;

    @Column(name = "collateral", nullable = false)
    private boolean collateral;

    // --- статус и решение ---
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private ApplicationStatus status;

    @Column(name = "decision_id")
    private String decisionId;

    @Column(name = "decision_comment", columnDefinition = "TEXT")
    private String decisionComment;

    // --- компромиссные условия ---
    @Column(name = "counter_rate", precision = 6, scale = 2)
    private BigDecimal counterRate;

    @Column(name = "counter_amount", precision = 15, scale = 2)
    private BigDecimal counterAmount;

    @Column(name = "counter_duration_years")
    private Integer counterDurationYears;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected CreditApplication() {
    }

    public static CreditApplication create(ClientPrincipal client, LoanTerms terms, ProductRef product) {
        CreditApplication a = new CreditApplication();
        a.clientLogin = client.login();
        a.clientInn = client.inn();
        a.organizationType = client.organizationType();
        a.rate = terms.rate();
        a.amount = terms.amount();
        a.durationYears = terms.durationYears();
        a.purpose = terms.purpose();
        a.collateral = terms.collateral();
        if (product != null) {
            a.productId = product.id();
            a.productTitle = product.title();
            a.productInterest = product.interest();
        }
        a.status = ApplicationStatus.UNDER_CONSIDERATION;
        a.createdAt = Instant.now();
        a.updatedAt = a.createdAt;
        return a;
    }

    /** Сохраняет id решения, если сервис принятия решений ответил асинхронно (заявка остаётся на рассмотрении) */
    public void attachDecisionId(String decisionId) {
        requireStatus(ApplicationStatus.UNDER_CONSIDERATION);
        this.decisionId = decisionId;
        touch();
    }

    /** Применяет итоговое решение банка, полученное из сервиса принятия решений */
    public void applyDecision(String decisionId, ApplicationStatus target, String comment, CounterOffer counterOffer) {
        requireStatus(ApplicationStatus.UNDER_CONSIDERATION);
        switch (target) {
            case ACCEPTED, REJECTED -> {
            }
            case COUNTER_OFFER -> {
                if (counterOffer == null) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "Для компромиссного решения не переданы условия");
                }
                this.counterRate = counterOffer.rate();
                this.counterAmount = counterOffer.amount();
                this.counterDurationYears = counterOffer.durationYears();
            }
            default -> throw new ApiException(HttpStatus.BAD_REQUEST, "Недопустимый итоговый статус: " + target);
        }
        this.status = target;
        this.decisionId = decisionId;
        this.decisionComment = comment;
        touch();
    }

    /** Клиент принимает или отклоняет компромиссные условия */
    public void respondToCounterOffer(boolean accept) {
        if (this.status != ApplicationStatus.COUNTER_OFFER) {
            throw new ApiException(HttpStatus.CONFLICT,
                    "Компромиссные условия не предлагались или уже обработаны. Текущий статус: " + this.status);
        }
        this.status = accept ? ApplicationStatus.ACCEPTED : ApplicationStatus.REJECTED;
        touch();
    }

    private void requireStatus(ApplicationStatus expected) {
        if (this.status != expected) {
            throw new ApiException(HttpStatus.CONFLICT,
                    "Операция недоступна для заявки в статусе " + this.status);
        }
    }

    private void touch() {
        this.updatedAt = Instant.now();
    }

    public CounterOffer getCounterOffer() {
        if (counterRate == null && counterAmount == null && counterDurationYears == null) {
            return null;
        }
        return new CounterOffer(counterRate, counterAmount, counterDurationYears);
    }

    public Long getId() { return id; }
    public Long getVersion() { return version; }
    public String getClientLogin() { return clientLogin; }
    public String getClientInn() { return clientInn; }
    public OrganizationType getOrganizationType() { return organizationType; }
    public Long getProductId() { return productId; }
    public String getProductTitle() { return productTitle; }
    public BigDecimal getProductInterest() { return productInterest; }
    public BigDecimal getRate() { return rate; }
    public BigDecimal getAmount() { return amount; }
    public int getDurationYears() { return durationYears; }
    public String getPurpose() { return purpose; }
    public boolean isCollateral() { return collateral; }
    public ApplicationStatus getStatus() { return status; }
    public String getDecisionId() { return decisionId; }
    public String getDecisionComment() { return decisionComment; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
