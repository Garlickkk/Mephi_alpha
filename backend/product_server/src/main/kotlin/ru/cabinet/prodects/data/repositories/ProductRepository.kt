package ru.cabinet.prodects.data.repositories

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import ru.cabinet.prodects.data.models.Product

@Repository
interface ProductRepository: JpaRepository<Product, Long> {
}