package ru.cabinet.prodects.data.dto

import ru.cabinet.prodects.data.models.TypeOfRepayment

data class ProductPost(
    val title: String,
    val purposes: String,
    val interest: Double,
    val discountInterest: Double,
    val discountConditions: String? = null,
    val minSum: Int,
    val maxSum: Int,
    val minDurationYear: Int,
    val maxDurationYear: Int,
    val repaymentTypes: Set<TypeOfRepayment>,
    val mainDifference: String
)