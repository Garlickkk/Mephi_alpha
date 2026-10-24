package ru.cabinet.user.auth.jwt

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.LoggerFactory
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken
import org.springframework.security.core.context.SecurityContextHolder
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter
import ru.cabinet.user.auth.users.CustomUserDetailService

@Component
class JwtAuthenticationFilter(
    private val tokenProvider: JwtTokenProvider,
    private val service: CustomUserDetailService
) : OncePerRequestFilter() {

    companion object {
        private const val HEADER = "Authorization"
        private const val PREFIX = "Bearer "
        private val log = LoggerFactory.getLogger(JwtAuthenticationFilter::class.java)
    }

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain
    ) {
        try {
            val token = getTokenFromRequest(request)

            if (token != null
                && SecurityContextHolder.getContext().authentication == null
                && tokenProvider.isAccessToken(token)
            ) {
                val username = tokenProvider.getUsername(token)
                val user = service.loadUserByUsername(username)

                val auth = UsernamePasswordAuthenticationToken(
                    user,
                    null,
                    user.authorities
                ).apply {
                    details = WebAuthenticationDetailsSource().buildDetails(request)
                }

                SecurityContextHolder.getContext().authentication = auth
            }
        } catch (ex: Exception) {
            log.debug("Cannot set user authentication: {}", ex.message)
            SecurityContextHolder.clearContext()
        }

        filterChain.doFilter(request, response)
    }

    private fun getTokenFromRequest(request: HttpServletRequest): String? {
        val bearer = request.getHeader(HEADER) ?: return null
        return if (bearer.startsWith(PREFIX)) bearer.substring(PREFIX.length) else null
    }
}