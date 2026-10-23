package ru.cabinet.prodects.data.models

import jakarta.persistence.CollectionTable
import jakarta.persistence.Column
import jakarta.persistence.ElementCollection
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.Table

@Entity
@Table(name="products")
data class Product(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long? = null,

    @Column(nullable = false, unique = true, length = 100)
    val title: String,

    // Цели кредита
    @Column(nullable = false, columnDefinition = "TEXT")
    val purposes: String,

    // Базовая ставка
    @Column(nullable = false)
    val interest: Double,

    // Ставка со скидкой
    @Column(nullable = false, name = "discount_interest")
    val discountInterest: Double,

    // Условия для получения скидки (например, "при оформлении Защиты бизнеса и Подписки")
    @Column(nullable = true, name = "discount_conditions", columnDefinition = "TEXT")
    val discountConditions: String?,

    @Column(nullable = false, name = "min_sum")
    val minSum: Int,

    @Column(nullable = false, name = "max_sum")
    val maxSum: Int,

    @Column(nullable = false, name = "min_duration")
    val minDurationYear: Int,

    @Column(nullable = false, name = "max_duration")
    val maxDurationYear: Int,

    // Способы погашения (может быть несколько, поэтому используем ElementCollection)
    @ElementCollection(targetClass = TypeOfRepayment::class)
    @CollectionTable(name = "product_repayment_types", joinColumns = [JoinColumn(name = "product_id")])
    @Enumerated(EnumType.STRING)
    @Column(name = "repayment_type")
    val repaymentTypes: Set<TypeOfRepayment>,

    // Главное отличие
    @Column(nullable = false, name = "main_difference", columnDefinition = "TEXT")
    val mainDifference: String
) {
    init {
        require(minSum >= 0) {
            "Минимальная сумма должна быть больше 0"
        }
        require(maxSum > minSum) {
            "Максимальная сумма должна быть больше минимальной"
        }

        require(minDurationYear >= 0) {
            "Минимальная длительность должна быть больше 0"
        }
        require(maxDurationYear > minDurationYear) {
            "Максимальная длительность должна быть больше минимальной"
        }

        // Дополнительные проверки
        require(interest > 0) {
            "Ставка должна быть больше 0"
        }
        require(discountInterest > 0 && discountInterest <= interest) {
            "Ставка со скидкой должна быть больше 0 и не превышать базовую ставку"
        }
    }
}

enum class TypeOfRepayment {
    // Равными частями по основному долгу (каждый месяц платёж становится меньше - аннуитетный/дифференцированный)
    EQUAL_PRINCIPAL_PARTS,

    // Равными частями по сумме кредита (каждый месяц платёж одинаковый - аннуитетный)
    EQUAL_TOTAL_PARTS
}
