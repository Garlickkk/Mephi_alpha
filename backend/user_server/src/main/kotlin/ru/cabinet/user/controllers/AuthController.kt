package ru.cabinet.user.controllers


import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.security.core.Authentication
import org.springframework.web.bind.annotation.*
import ru.cabinet.user.data.models.LoginRequest
import ru.cabinet.user.data.models.RefreshRequest
import ru.cabinet.user.data.models.RegisterRequest
import ru.cabinet.user.data.models.TokenResponse
import ru.cabinet.user.data.services.AuthService


@RestController
@RequestMapping("/api/v0/auth")
class AuthController(
    private val authService: AuthService
) {

    @PostMapping("/login")
    fun login(@RequestBody request: LoginRequest): TokenResponse =
        authService.login(request)

    @PostMapping("/refresh")
    fun refresh(@RequestBody request: RefreshRequest): TokenResponse =
        authService.refresh(request.refreshToken)

    @PostMapping("/logout")
    fun logout(authentication: Authentication): ResponseEntity<Void> {
        authService.logout(authentication.name)
        return ResponseEntity.noContent().build()
    }
    @PostMapping("/register")
    fun register(@RequestBody request: RegisterRequest): ResponseEntity<TokenResponse> =
        ResponseEntity.status(HttpStatus.CREATED).body(authService.register(request))
}