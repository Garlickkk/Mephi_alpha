package ru.cabinet.prodects.data.dto

import ru.cabinet.prodects.data.models.TypeOfRepayment

data class ProductGet(
    val id: Long,
    val title: String,
    val purposes: String,
    val interest: Double,
    val discountInterest: Double,
    val discountConditions: String?,
    val minSum: Int,
    val maxSum: Int,
    val minDurationYear: Int,
    val maxDurationYear: Int,
    val repaymentTypes: Set<TypeOfRepayment>,
    val mainDifference: String
)