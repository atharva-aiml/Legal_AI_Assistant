package com.legalai.backend.web;

/** Matches the `{ error: { code, message } }` shape every backend has used since the TS version (System Architecture §7). */
public record ApiError(ErrorBody error) {
    public record ErrorBody(String code, String message) {
    }

    public static ApiError of(String code, String message) {
        return new ApiError(new ErrorBody(code, message));
    }

    public static ApiError unauthenticated() {
        return of("UNAUTHENTICATED", "Not signed in");
    }

    public static ApiError notFound(String message) {
        return of("NOT_FOUND", message);
    }
}
