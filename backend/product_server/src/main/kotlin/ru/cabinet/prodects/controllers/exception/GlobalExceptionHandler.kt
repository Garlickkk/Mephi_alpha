package ru.cabinet.prodects.controllers.exception

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import ru.cabinet.prodects.data.dto.ApiResponse
import ru.cabinet.prodects.data.models.ProductNotFoundedException

@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(ProductNotFoundedException::class)
    fun handleProductNotFound(e: ProductNotFoundedException): ResponseEntity<ApiResponse> {
        return ResponseEntity.status(404).body(ApiResponse(e.message.toString()))
    }

    @ExceptionHandler(Exception::class)
    fun handleOtherException(e: Exception): ResponseEntity<ApiResponse> {
        return ResponseEntity.status(500).body(ApiResponse(e.message.toString()))
    }
}