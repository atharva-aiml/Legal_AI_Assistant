package com.legalai.backend.web;

import com.legalai.backend.application.auth.AuthService;
import com.legalai.backend.application.auth.SessionToken;
import com.legalai.backend.domain.Lawyer;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * Called explicitly at the top of every controller method that needs
 * auth — not a global filter alone. Mirrors the CLAUDE.md gotcha this
 * project has carried since the original TypeScript implementation:
 * middleware/filters are a UX shortcut, this resolver is the real
 * authorization boundary.
 */
@Component
public class CurrentLawyerResolver {

    private final AuthService authService;

    public CurrentLawyerResolver(AuthService authService) {
        this.authService = authService;
    }

    public Optional<Lawyer> resolve(HttpServletRequest request) {
        if (request.getCookies() == null) return Optional.empty();
        for (Cookie cookie : request.getCookies()) {
            if (SessionToken.COOKIE_NAME.equals(cookie.getName())) {
                return authService.resolveSession(cookie.getValue());
            }
        }
        return Optional.empty();
    }
}
