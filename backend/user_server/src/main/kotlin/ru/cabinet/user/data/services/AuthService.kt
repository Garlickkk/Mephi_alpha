package ru.cabinet.user.data.services

import jakarta.transaction.Transactional
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.authentication.AuthenticationManager
import org.springframework.security.authentication.BadCredentialsException
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service
import ru.cabinet.user.auth.jwt.JwtTokenProvider
import ru.cabinet.user.auth.jwt.TokenService
import ru.cabinet.user.auth.users.CustomUserDetailService
import ru.cabinet.user.auth.users.SecurityRole
import ru.cabinet.user.data.models.LoginRequest
import ru.cabinet.user.data.models.RegisterRequest
import ru.cabinet.user.data.models.TokenResponse
import ru.cabinet.user.data.models.UserEntity
import ru.cabinet.user.data.repositories.UserRepository

@Service
@Transactional
class AuthService(
    private val authenticationManager: AuthenticationManager,
    private val tokenProvider: JwtTokenProvider,
    private val tokenService: TokenService,
    private val userDetailsService: CustomUserDetailService,
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,

    @Value("\${test.access-token-expiration}")
    private val accessTokenExpiration: Long
) {
    companion object {
        private const val MIN_PASSWORD_LENGTH = 8
        private val log = LoggerFactory.getLogger(AuthService::class.java)
    }

    /** Логин по логину/паролю → пара токенов. */
    fun login(request: LoginRequest): TokenResponse {
        authenticationManager.authenticate(
            UsernamePasswordAuthenticationToken(request.login, request.password)
        )

        // 2. Загружаем UserDetails для выпуска токена
        val userDetails = userDetailsService.loadUserByUsername(request.login)

        // 3. Генерируем токены
        val accessToken = tokenProvider.generateAccessToken(userDetails)
        val refreshToken = tokenProvider.generateRefreshToken(userDetails)

        // 4. Refresh кладём в БД, чтобы можно было отозвать/валидировать
        tokenService.saveRefreshTokenInDB(request.login, refreshToken)

        log.info("User logged in: login={}", request.login)
        return buildResponse(accessToken, refreshToken)
    }

    /** Обновление пары по refresh-токену (с ротацией refresh). */
    fun refresh(refreshToken: String): TokenResponse {
        if (!tokenProvider.validateToken(refreshToken) || !tokenProvider.isRefreshToken(refreshToken)) {
            throw BadCredentialsException("Invalid refresh token")
        }

        val login = tokenProvider.getUsername(refreshToken)

        // Сверка с БД: токен должен совпадать с сохранённым и не истёк
        if (!tokenService.validateRefreshToken(login, refreshToken)) {
            throw BadCredentialsException("Refresh token revoked or expired")
        }

        val userDetails = userDetailsService.loadUserByUsername(login)

        val newAccessToken = tokenProvider.generateAccessToken(userDetails)
        val newRefreshToken = tokenProvider.generateRefreshToken(userDetails)

        // Ротация: старый refresh перезаписывается новым
        tokenService.saveRefreshTokenInDB(login, newRefreshToken)

        log.info("Tokens refreshed: login={}", login)
        return buildResponse(newAccessToken, newRefreshToken)
    }

    fun register(request: RegisterRequest): TokenResponse {
        // 1. Валидация
        require(request.login.isNotBlank()) { "login must not be blank" }
        require(request.password.length >= MIN_PASSWORD_LENGTH) {
            "password must be at least $MIN_PASSWORD_LENGTH chars"
        }
        require(request.inn.isNotBlank()) { "inn must not be blank" }
        require(request.ogrn.isNotBlank()) { "ogrn must not be blank" }

        // 2. Уникальность
        if (userRepository.findUserEntityByLogin(request.login) != null) {
            throw IllegalArgumentException("User with login=${request.login} already exists")
        }
        // Если в БД есть unique-констрейнты на inn/ogrn — лучше проверить явно,
        // чтобы вернуть 400, а не 500 от DataIntegrityViolationException.
        if (userRepository.existsByInn(request.inn)) {
            throw IllegalArgumentException("User with inn=${request.inn} already exists")
        }
        if (userRepository.existsByOgrn(request.ogrn)) {
            throw IllegalArgumentException("User with ogrn=${request.ogrn} already exists")
        }

        // 3. Создание. Роль всегда USER — клиент не может прислать ADMIN.
        val entity = UserEntity(
            firstName = request.firstName,
            lastName = request.lastName,
            secondName = request.secondName,
            organizationType = request.organizationType,
            inn = request.inn,
            registrationDate = request.registrationDate,
            okved = request.okved,
            ogrn = request.ogrn,
            password = checkNotNull(passwordEncoder.encode(request.password)) { "Пароль не может быть null" },
            login = request.login,
            roles = listOf(SecurityRole.CLIENT)
        )
        userRepository.save(entity)

        // 4. Сразу логиним — выпускаем токены
        val userDetails = userDetailsService.loadUserByUsername(request.login)
        val accessToken = tokenProvider.generateAccessToken(userDetails)
        val refreshToken = tokenProvider.generateRefreshToken(userDetails)
        tokenService.saveRefreshTokenInDB(request.login, refreshToken)

        log.info("User registered: login={}", request.login)
        return buildResponse(accessToken, refreshToken)
    }

    /** Выход: отзываем refresh в БД. Access живёт до истечения (stateless). */
    fun logout(login: String) {
        tokenService.revokeRefreshToken(login)
        log.info("User logged out: login={}", login)
    }

    private fun buildResponse(accessToken: String, refreshToken: String) =
        TokenResponse(
            accessToken = accessToken,
            refreshToken = refreshToken,
            expiresIn = accessTokenExpiration / 1000   // конфиг в мс → секунды
        )
}