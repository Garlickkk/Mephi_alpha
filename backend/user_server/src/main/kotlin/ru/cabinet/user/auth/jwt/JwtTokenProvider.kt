package ru.cabinet.user.auth.jwt

import io.jsonwebtoken.Claims
import io.jsonwebtoken.JwtException
import io.jsonwebtoken.Jwts
import io.jsonwebtoken.security.Keys
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.core.GrantedAuthority
import org.springframework.security.core.authority.SimpleGrantedAuthority
import org.springframework.security.core.userdetails.UserDetails
import org.springframework.stereotype.Component
import ru.cabinet.user.auth.users.CustomUserDetails
import java.nio.charset.StandardCharsets
import java.time.LocalDate
import java.util.Date

@Component
class JwtTokenProvider(
    @Value("\${test.secret.key}") secret: String,
    @Value("\${test.refresh-token-expiration}") private val refreshTokenExpiration: Long,
    @Value("\${test.access-token-expiration}") private val accessTokenExpiration: Long
) {
    companion object {
        private const val TOKEN_TYPE = "type"
        private const val ACCESS_TOKEN = "access"
        private const val REFRESH_TOKEN = "refresh"
        private const val AUTHORITIES = "authorities"
        private const val ORGANIZATION_TYPE = "organization_type"
        private const val INN = "inn"
        private const val OKVED_MAIN = "okved_main"
        private const val REGISTRATION_DATE = "registration_date"

        private val log = LoggerFactory.getLogger(JwtTokenProvider::class.java)
    }

    private val secretKeySpec = Keys.hmacShaKeyFor(secret.toByteArray(StandardCharsets.UTF_8))



    fun generateAccessToken(userDetails: UserDetails): String =
        buildToken(userDetails, ACCESS_TOKEN, accessTokenExpiration)

    fun generateRefreshToken(userDetails: UserDetails): String =
        buildToken(userDetails, REFRESH_TOKEN, refreshTokenExpiration)

    private fun buildToken(userDetails: UserDetails, type: String, expirationMs: Long): String {
        val custom = userDetails as CustomUserDetails
        return Jwts.builder()
            .subject(custom.username)
            .claim(TOKEN_TYPE, type)
            .claim(INN, custom.inn)
            .claim(ORGANIZATION_TYPE, custom.type)
            .claim(OKVED_MAIN, custom.okvedMain)
            .claim(REGISTRATION_DATE, custom.registrationDate?.toString())
            .claim(AUTHORITIES, custom.authorities.map(GrantedAuthority::getAuthority))
            .issuedAt(Date())
            .expiration(Date(System.currentTimeMillis() + expirationMs))
            .signWith(secretKeySpec)
            .compact()
    }



    fun parseClaims(token: String): Claims =
        Jwts.parser()
            .verifyWith(secretKeySpec)
            .build()
            .parseSignedClaims(token)
            .payload

    fun getUsername(token: String): String = parseClaims(token).subject

    fun getTokenType(token: String): String? = parseClaims(token)[TOKEN_TYPE] as? String

    fun getAuthorities(token: String): List<GrantedAuthority> {
        val raw = parseClaims(token)[AUTHORITIES] as? List<*> ?: return emptyList()
        return raw.mapNotNull { it as? String }
            .map { SimpleGrantedAuthority(it) }
    }

    fun getInn(token: String): String? = parseClaims(token)[INN] as? String

    fun getOrganizationType(token: String): String? = parseClaims(token)[ORGANIZATION_TYPE] as? String

    fun getOkvedMain(token: String): String? = parseClaims(token)[OKVED_MAIN] as? String

    fun getRegistrationDate(token: String): LocalDate? =
        (parseClaims(token)[REGISTRATION_DATE] as? String)?.let(LocalDate::parse)

    fun getExpiration(token: String): Date = parseClaims(token).expiration



    fun validateToken(token: String): Boolean = try {
        parseClaims(token)
        true
    } catch (ex: JwtException) {
        log.debug("Invalid JWT: {}", ex.message)
        false
    } catch (ex: IllegalArgumentException) {
        log.debug("JWT is empty or malformed: {}", ex.message)
        false
    }

    fun isAccessToken(token: String): Boolean =
        validateToken(token) && getTokenType(token) == ACCESS_TOKEN

    fun isRefreshToken(token: String): Boolean =
        validateToken(token) && getTokenType(token) == REFRESH_TOKEN

    fun isTokenExpired(token: String): Boolean = try {
        getExpiration(token).before(Date())
    } catch (ex: JwtException) {
        true
    }
}