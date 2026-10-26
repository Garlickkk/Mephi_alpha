package ru.cabinet.user.api.services

import org.slf4j.LoggerFactory
import org.springframework.security.core.userdetails.UsernameNotFoundException
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import ru.cabinet.user.auth.jwt.TokenService
import ru.cabinet.user.auth.users.SecurityRole
import ru.cabinet.user.data.models.ChangePasswordRequest
import ru.cabinet.user.data.models.CreateUserRequest
import ru.cabinet.user.data.models.MeResponse
import ru.cabinet.user.data.models.UpdateUserRequest
import ru.cabinet.user.data.models.UserEntity
import ru.cabinet.user.data.models.UserResponse
import ru.cabinet.user.data.repositories.UserRepository

@Service
class UserService(
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,
    private val tokenService: TokenService
) {
    companion object {
        private val log = LoggerFactory.getLogger(UserService::class.java)
    }


    @Transactional(readOnly = true)
    fun getAll(): List<UserResponse> =
        userRepository.findAll().map { it.toResponse() }

    @Transactional(readOnly = true)
    fun getByLogin(login: String): UserResponse =
        getUserByLogin(login).toResponse()

    @Transactional(readOnly = true)
    fun getById(id: Long): UserResponse =
        userRepository.findById(id)
            .orElseThrow { UsernameNotFoundException("User id=$id not found") }
            .toResponse()

    fun me(accessToken: String): MeResponse {
        val claims = tokenService.extractUserClaims(accessToken)
        val user = userRepository.findUserEntityByLogin(claims.username)
            ?: throw UsernameNotFoundException("User with login=${claims.username} not found")

        return MeResponse(
            login = user.login,
            firstName = user.firstName,
            lastName = user.lastName,
            secondName = user.secondName,
            organizationType = user.organizationType.name,
            inn = claims.inn ?: user.inn,
            ogrn = user.ogrn,
            okved = claims.okvedMain ?: user.okved,
            registrationDate = claims.registrationDate ?: user.registrationDate,
            authorities = claims.authorities
        )
    }


    @Transactional
    fun create(request: CreateUserRequest): UserResponse {
        require(request.login.isNotBlank()) { "login must not be blank" }
        require(request.password.length >= 8) { "password must be at least 8 chars" }
        require(request.inn.isNotBlank()) { "inn must not be blank" }
        require(request.ogrn.isNotBlank()) { "ogrn must not be blank" }

        if (userRepository.findUserEntityByLogin(request.login) != null) {
            throw IllegalArgumentException("User with login=${request.login} already exists")
        }

        val entity = UserEntity(
            firstName = request.firstName,
            lastName = request.lastName,
            secondName = request.secondName,
            organizationType = request.organizationType,
            inn = request.inn,
            registrationDate = request.registrationDate,
            okved = request.okved,
            ogrn = request.ogrn,
            password = passwordEncoder.encode(request.password)!!,
            login = request.login,
            roles = request.roles.map { SecurityRole.valueOf(it) }
        )

        val saved = userRepository.save(entity)
        log.info("User created: login={}", saved.login)
        return saved.toResponse()
    }


    @Transactional
    fun update(login: String, request: UpdateUserRequest): UserResponse {
        val user = getUserByLogin(login)

        request.firstName?.let { user.firstName = it }
        request.lastName?.let { user.lastName = it }
        request.secondName?.let { user.secondName = it }
        request.okved?.let { user.okved = it }
        request.roles?.let { user.roles = it.map(SecurityRole::valueOf) }

        val saved = userRepository.save(user)
        log.info("User updated: login={}", saved.login)
        return saved.toResponse()
    }

    @Transactional
    fun changePassword(login: String, request: ChangePasswordRequest) {
        val user = getUserByLogin(login)
        if (!passwordEncoder.matches(request.oldPassword, user.password)) {
            throw IllegalArgumentException("Old password is incorrect")
        }
        require(request.newPassword.length >= 8) { "password must be at least 8 chars" }
        userRepository.updatePasswordByLogin(login, passwordEncoder.encode(request.newPassword)!!)
        log.info("Password changed: login={}", login)
    }


    @Transactional
    fun delete(login: String) {
        val user = getUserByLogin(login)
        userRepository.delete(user)
        log.info("User deleted: login={}", login)
    }

    private fun getUserByLogin(login: String): UserEntity =
        userRepository.findUserEntityByLogin(login)
            ?: throw UsernameNotFoundException("User with login=$login not found")

    private fun UserEntity.toResponse() = UserResponse(
        id = id,
        login = login,
        firstName = firstName,
        lastName = lastName,
        secondName = secondName,
        organizationType = organizationType,
        inn = inn,
        ogrn = ogrn,
        registrationDate = registrationDate,
        okved = okved,
        roles = roles.map { it.name }
    )
}