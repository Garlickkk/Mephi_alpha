package ru.cabinet.applications.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import ru.cabinet.applications.data.OrganizationType;
import ru.cabinet.applications.exception.ApiException;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;

@Component
public class JwtService {

    // имена claim'ов должны совпадать с user_server/JwtTokenProvider
    private static final String TOKEN_TYPE = "type";
    private static final String ACCESS_TOKEN = "access";
    private static final String INN = "inn";
    private static final String ORGANIZATION_TYPE = "organization_type";
    private static final String OKVED_MAIN = "okved_main";
    private static final String REGISTRATION_DATE = "registration_date";

    private final SecretKey key;

    public JwtService(@Value("${app.jwt.secret}") String secret) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public ClientPrincipal parseAccessToken(String token) {
        Claims claims;
        try {
            claims = Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (JwtException | IllegalArgumentException e) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Токен недействителен или истёк");
        }

        if (!ACCESS_TOKEN.equals(claims.get(TOKEN_TYPE, String.class))) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Ожидался access-токен");
        }

        return new ClientPrincipal(
                claims.getSubject(),
                claims.get(INN, String.class),
                parseOrganizationType(claims.get(ORGANIZATION_TYPE, String.class)),
                claims.get(OKVED_MAIN, String.class),
                parseDate(claims.get(REGISTRATION_DATE, String.class))
        );
    }

    private static OrganizationType parseOrganizationType(String raw) {
        if (raw == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "В токене нет типа организации");
        }
        try {
            return OrganizationType.valueOf(raw);
        } catch (IllegalArgumentException e) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Неизвестный тип организации в токене: " + raw);
        }
    }

    private static LocalDate parseDate(String raw) {
        return raw == null ? null : LocalDate.parse(raw);
    }
}
