package ru.cabinet.user

import org.junit.jupiter.api.Test
import org.mockito.Mockito.`when`
import org.mockito.Mockito.verify
import org.mockito.Mockito.verifyNoInteractions
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest
import org.springframework.context.annotation.Import
import org.springframework.security.test.context.support.WithMockUser
import org.springframework.test.context.bean.override.mockito.MockitoBean
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.*
import ru.cabinet.user.api.services.UserService
import ru.cabinet.user.auth.config.SecurityConfig
import ru.cabinet.user.auth.jwt.JwtAuthenticationFilter
import ru.cabinet.user.auth.jwt.JwtTokenProvider
import ru.cabinet.user.auth.users.CustomUserDetailService
import ru.cabinet.user.controllers.UserController
import ru.cabinet.user.data.models.OrganizationType
import ru.cabinet.user.data.models.UserResponse
import java.time.LocalDate

@WebMvcTest(UserController::class)
@Import(SecurityConfig::class, JwtAuthenticationFilter::class)
class ProfileAccessTests {
    @Autowired
    lateinit var mvc: MockMvc

    @MockitoBean
    lateinit var userService: UserService

    @MockitoBean
    lateinit var tokenProvider: JwtTokenProvider

    @MockitoBean
    lateinit var userDetailsService: CustomUserDetailService

    @Test
    @WithMockUser(username = "client", roles = ["CLIENT"])
    fun `client can load own profile using authenticated identity`() {
        `when`(userService.getByLogin("client")).thenReturn(UserResponse(
            id = 1L, login = "client", firstName = "Иван", lastName = "Иванов",
            secondName = "", organizationType = OrganizationType.IP, inn = "770000000001",
            ogrn = "123456789012345", registrationDate = LocalDate.of(2020, 1, 1),
            okved = "62.01", roles = listOf("CLIENT")
        ))

        mvc.perform(get("/api/v0/users/me").param("login", "another-user"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.login").value("client"))
            .andExpect(jsonPath("$.organizationType").value("IP"))
            .andExpect(jsonPath("$.inn").value("770000000001"))
        verify(userService).getByLogin("client")
    }

    @Test
    fun `anonymous request returns 401 so frontend can refresh or request login`() {
        mvc.perform(get("/api/v0/users/me")).andExpect(status().isUnauthorized)
        verifyNoInteractions(userService)
    }

    @Test
    @WithMockUser(username = "client", roles = ["CLIENT"])
    fun `client cannot read other accounts or list all users`() {
        mvc.perform(get("/api/v0/users/another-user")).andExpect(status().isForbidden)
        mvc.perform(get("/api/v0/users")).andExpect(status().isForbidden)
        verifyNoInteractions(userService)
    }
}
