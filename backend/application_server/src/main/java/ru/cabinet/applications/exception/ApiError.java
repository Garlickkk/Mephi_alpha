package ru.cabinet.applications.exception;

import java.time.LocalDateTime;

/** Единый формат ошибки, как в product_server */
public record ApiError(String message, LocalDateTime dateTime) {}
