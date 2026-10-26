package ru.cabinet.user.data.models

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import ru.cabinet.user.auth.users.SecurityRole
import java.time.LocalDate
import java.time.LocalDateTime

@Table(name = "users")
@Entity
data class UserEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long? = null,

    @Column(name = "first_name", nullable = false)
    var firstName: String,

    @Column(name = "last_name", nullable = false)
    var lastName: String,

    @Column(name = "second_name", nullable = false)
    var secondName: String,

    @Column(name = "organization_type", nullable = false)
    @Enumerated(EnumType.STRING)
    val organizationType: OrganizationType,

    @Column(name = "inn", nullable = false, unique = true)
    val inn: String,

    @Column(name = "registration_date", nullable = false)
    val registrationDate: LocalDate,

    @Column(name = "okved", nullable = false, columnDefinition = "TEXT")
    var okved: String,

    @Column(name = "ogrn", nullable = false, unique = true)
    val ogrn: String,

    @Column(name = "password", nullable = false, columnDefinition = "TEXT")
    val password: String,

    @Column(name = "login", nullable = false)
    val login: String,

    @Column(name = "refresh_token", columnDefinition = "TEXT")
    var refreshToken: String? = null,

    @Column(name = "refresh_expire")
    var refreshTokenExpire: LocalDateTime? = null,

    @Column(name = "roles")
    var roles: List<SecurityRole>
)

enum class OrganizationType {
    OOO,
    IP,
    AO
}