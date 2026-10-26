package ru.cabinet.applications.security;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** Внедряет ClientPrincipal, распарсенный из заголовка Authorization: Bearer <jwt> */
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
public @interface CurrentClient {
}
