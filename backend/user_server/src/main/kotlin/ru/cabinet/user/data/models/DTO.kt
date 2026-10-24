package ru.cabinet.user.data.models

import java.time.LocalDate

data class UserResponse(
    val id: Long?,
    val login: String,
    val firstName: String,
    val lastName: String,
    val secondName: String,
    val organizationType: OrganizationType,
    val inn: String,
    val ogrn: String,
    val registrationDate: LocalDate,
    val okved: String,
    val roles: List<String>          // "USER", "ADMIN" — без префикса ROLE_
)

data class CreateUserRequest(
    val login: String,
    val password: String,
    val firstName: String,
    val lastName: String,
    val secondName: String,
    val organizationType: OrganizationType,
    val inn: String,
    val ogrn: String,
    val registrationDate: LocalDate,
    val okved: String,
    val roles: List<String> = listOf("USER")
)

/** Поля, которые реально можно менять (остальные — val). */
data class UpdateUserRequest(
    val firstName: String? = null,
    val lastName: String? = null,
    val secondName: String? = null,
    val okved: String? = null,
    val roles: List<String>? = null
)

/** Смена пароля — отдельным запросом, т.к. password в entity — val. */
data class ChangePasswordRequest(
    val oldPassword: String,
    val newPassword: String
)

data class MeResponse(
    val login: String,
    val firstName: String,
    val lastName: String,
    val secondName: String,
    val organizationType: String?,
    val inn: String?,
    val ogrn: String?,
    val okved: String?,
    val registrationDate: LocalDate?,
    val authorities: List<String>
)

data class LoginRequest(
    val login: String,
    val password: String
)

data class RefreshRequest(
    val refreshToken: String
)

data class TokenResponse(
    val accessToken: String,
    val refreshToken: String,
    val tokenType: String = "Bearer",
    val expiresIn: Long
)

data class RegisterRequest(
    val login: String,
    val password: String,
    val firstName: String,
    val lastName: String,
    val secondName: String,
    val organizationType: OrganizationType,
    val inn: String,
    val ogrn: String,
    val registrationDate: LocalDate,
    val okved: String
)