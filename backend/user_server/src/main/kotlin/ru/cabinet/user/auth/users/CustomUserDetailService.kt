package ru.cabinet.user.auth.users

import org.springframework.security.core.authority.SimpleGrantedAuthority
import org.springframework.security.core.userdetails.UserDetails
import org.springframework.security.core.userdetails.UserDetailsService
import org.springframework.stereotype.Service
import ru.cabinet.user.data.models.UserNotFoundException
import ru.cabinet.user.data.repositories.UserRepository

@Service
class CustomUserDetailService(private val userRepository: UserRepository) : UserDetailsService {
    override fun loadUserByUsername(login: String): UserDetails {
        val user = userRepository.findUserEntityByLogin(login)
            ?: throw UserNotFoundException("User with inn=$login not found")

        return CustomUserDetails(
            login = login,
            password = user.password,
            inn = user.inn,
            registrationDate = user.registrationDate,
            okvedMain = user.okved,
            authorities = authorities(),
            type = user.organizationType
        )
    }

    private fun authorities(secRole: SecurityRole = SecurityRole.CLIENT) =
        listOf(SimpleGrantedAuthority("ROLE_${secRole.name}"))
}