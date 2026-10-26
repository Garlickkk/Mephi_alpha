package ru.cabinet.user.controllers


import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.web.bind.annotation.*
import ru.cabinet.user.api.services.UserService
import ru.cabinet.user.data.models.CreateUserRequest
import ru.cabinet.user.data.models.MeResponse
import ru.cabinet.user.data.models.UpdateUserRequest
import ru.cabinet.user.data.models.UserResponse

@RestController
@RequestMapping("/api/v0/users")
class UserController(private val userService: UserService) {

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")                 // только админ
    fun getAll() = userService.getAll()

    @GetMapping("/{login}")
    @PreAuthorize("hasRole('ADMIN') or #login == authentication.name")  // админ или сам
    fun getByLogin(@PathVariable login: String) = userService.getByLogin(login)

}