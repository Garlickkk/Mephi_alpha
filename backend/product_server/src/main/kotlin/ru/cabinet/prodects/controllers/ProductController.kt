package ru.cabinet.prodects.controllers

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RestController
import ru.cabinet.prodects.data.ProductService
import ru.cabinet.prodects.data.dto.ProductGet
import ru.cabinet.prodects.data.dto.ProductGetContainer

@RestController
class ProductController(private val productService: ProductService) {
    @GetMapping("/products")
    fun getAllProducts(): ProductGetContainer {
        return productService.getAllProducts();
    }

    @GetMapping("/products/{id}")
    fun getProductById(@PathVariable id: Long): ResponseEntity<ProductGet>{
        return ResponseEntity.ok(productService.getProductById(id))
    }
}