package ru.cabinet.user.auth.jwt

import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.core.userdetails.UsernameNotFoundException
import org.springframework.stereotype.Component
import ru.cabinet.user.data.models.UserEntity
import ru.cabinet.user.data.repositories.UserRepository
import java.time.LocalDate
import java.time.LocalDateTime

@Component
class TokenService(
    private val userRepository: UserRepository,
    private val tokenProvider: JwtTokenProvider,

    @Value("\${test.refresh-token-expiration}")
    private val expirationRefreshToken: Long
) {
    companion object {
        private val log = LoggerFactory.getLogger(TokenService::class.java)
    }

    /** Сохраняет refresh-токен и срок его жизни для пользователя с указанным login. */
    fun saveRefreshTokenInDB(login: String, refreshToken: String) {
        userRepository.updateUserByLogin(
            refreshToken,
            LocalDateTime.now().plusSeconds(expirationRefreshToken / 1000),
            login
        )
    }

    fun getRefreshTokenByLogin(login: String): String? =
        getUserByLogin(login).refreshToken

    fun getTokenInfo(login: String): TokenInfo {
        val user = getUserByLogin(login)
        return TokenInfo(user.refreshToken, user.refreshTokenExpire)
    }

    fun validateRefreshToken(login: String, refreshToken: String): Boolean = try {
        val info = getTokenInfo(login)
        val stored = info.refreshToken
        val expiresAt = info.expiresAt

        stored != null &&
                expiresAt != null &&
                stored == refreshToken &&
                expiresAt.isAfter(LocalDateTime.now()) &&
                tokenProvider.validateToken(refreshToken) &&
                tokenProvider.isRefreshToken(refreshToken)
    } catch (ex: Exception) {
        log.debug("Refresh token validation failed for login={}: {}", login, ex.message)
        false
    }


    fun revokeRefreshToken(login: String) {
        userRepository.updateUserByLogin(null, null, login)
    }


    fun extractUserClaims(accessToken: String): UserTokenClaims {
        require(tokenProvider.isAccessToken(accessToken)) { "Invalid or expired access token" }
        return UserTokenClaims(
            username = tokenProvider.getUsername(accessToken),
            inn = tokenProvider.getInn(accessToken),
            organizationType = tokenProvider.getOrganizationType(accessToken),
            okvedMain = tokenProvider.getOkvedMain(accessToken),
            registrationDate = tokenProvider.getRegistrationDate(accessToken),
            authorities = getAuthorities(accessToken)
        )
    }

    fun getInn(accessToken: String): String? = tokenProvider.getInn(accessToken)

    fun getOrganizationType(accessToken: String): String? =
        tokenProvider.getOrganizationType(accessToken)

    fun getOkvedMain(accessToken: String): String? = tokenProvider.getOkvedMain(accessToken)

    fun getRegistrationDate(accessToken: String): LocalDate? =
        tokenProvider.getRegistrationDate(accessToken)

    fun getAuthorities(accessToken: String): List<String> =
        tokenProvider.getAuthorities(accessToken).mapNotNull { it.authority }


    private fun getUserByLogin(login: String): UserEntity =
        userRepository.findUserEntityByLogin(login)
            ?: throw UsernameNotFoundException("User with login=$login not found")
}

data class UserTokenClaims(
    val username: String,
    val inn: String?,
    val organizationType: String?,
    val okvedMain: String?,
    val registrationDate: LocalDate?,
    val authorities: List<String>
)

data class TokenInfo(
    val refreshToken: String?,
    val expiresAt: LocalDateTime?
)