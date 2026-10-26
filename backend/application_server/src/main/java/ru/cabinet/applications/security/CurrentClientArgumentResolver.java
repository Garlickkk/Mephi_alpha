package ru.cabinet.applications.security;

import org.springframework.core.MethodParameter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;
import ru.cabinet.applications.exception.ApiException;

public class CurrentClientArgumentResolver implements HandlerMethodArgumentResolver {

    private static final String PREFIX = "Bearer ";

    private final JwtService jwtService;

    public CurrentClientArgumentResolver(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.hasParameterAnnotation(CurrentClient.class)
                && parameter.getParameterType().equals(ClientPrincipal.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter,
                                  ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest,
                                  WebDataBinderFactory binderFactory) {
        String header = webRequest.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith(PREFIX)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Требуется заголовок Authorization: Bearer <token>");
        }
        return jwtService.parseAccessToken(header.substring(PREFIX.length()).trim());
    }
}
