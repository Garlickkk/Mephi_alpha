package ru.cabinet.prodects.data

import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional  // ← ВАЖНО
import ru.cabinet.prodects.data.dto.ProductGet
import ru.cabinet.prodects.data.dto.ProductGetContainer
import ru.cabinet.prodects.data.models.Product
import ru.cabinet.prodects.data.models.ProductNotFoundedException
import ru.cabinet.prodects.data.repositories.ProductRepository

@Service
@Transactional(readOnly = true)
class ProductService(
    private val productRepository: ProductRepository
) {
    fun getAllProducts(): ProductGetContainer {
        val products = productRepository.findAll().map { it.toGet() }
        return ProductGetContainer(products = products)
    }

    fun getProductById(id: Long): ProductGet {
        val product = productRepository.findById(id)
            .orElseThrow { ProductNotFoundedException("Product with id=$id not found") }
        return product.toGet()
    }
}

fun Product.toGet() = ProductGet(
    id = checkNotNull(id) { "Product id is NULL" },
    title = title,
    purposes = purposes,
    interest = interest,
    discountInterest = discountInterest,
    discountConditions = discountConditions,
    minSum = minSum,
    maxSum = maxSum,
    minDurationYear = minDurationYear,
    maxDurationYear = maxDurationYear,
    repaymentTypes = repaymentTypes.toSet(),
    mainDifference = mainDifference
)