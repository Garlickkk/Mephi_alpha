package ru.cabinet.user.auth.users

import org.springframework.security.core.GrantedAuthority
import org.springframework.security.core.userdetails.UserDetails
import ru.cabinet.user.data.models.OrganizationType
import java.time.LocalDate

class CustomUserDetails(
    val login: String,
    @get:JvmName("getPasswordInternal")
    val password: String,
    val inn: String,
    val type: OrganizationType,
    val okvedMain: String,
    val registrationDate: LocalDate,
    @get:JvmName("getAuthoritiesInternal")
    val authorities: Collection<out GrantedAuthority>
) : UserDetails {
    override fun getAuthorities() = authorities

    override fun getPassword(): String = password

    override fun getUsername() = login
}