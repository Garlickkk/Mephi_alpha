package ru.cabinet.prodects.data.dto

import java.time.LocalDateTime

data class ApiResponse(
    val message: String,
    val dateTime: LocalDateTime = LocalDateTime.now(),
)