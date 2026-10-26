package ru.cabinet.user.controllers


import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.web.bind.annotation.*
import ru.cabinet.user.api.services.UserService
import java.security.Principal

@RestController
@RequestMapping("/api/v0/users")
class UserController(private val userService: UserService) {

    @GetMapping("/me")
    fun me(principal: Principal) = userService.getByLogin(principal.name)

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")                 // только админ
    fun getAll() = userService.getAll()

    @GetMapping("/{login}")
    @PreAuthorize("hasRole('ADMIN') or #login == authentication.name")  // админ или сам
    fun getByLogin(@PathVariable login: String) = userService.getByLogin(login)

}
