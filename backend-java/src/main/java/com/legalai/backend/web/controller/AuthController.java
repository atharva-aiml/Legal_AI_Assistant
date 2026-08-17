package com.legalai.backend.web.controller;

import com.legalai.backend.application.auth.AuthService;
import com.legalai.backend.application.auth.SessionToken;
import com.legalai.backend.application.preferences.LawyerPreferencesService;
import com.legalai.backend.domain.InvalidLawyerException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.AuthDtos.ChangePasswordRequest;
import com.legalai.backend.web.dto.AuthDtos.LoginRequest;
import com.legalai.backend.web.dto.AuthDtos.PreferencesResponse;
import com.legalai.backend.web.dto.AuthDtos.RegisterRequest;
import com.legalai.backend.web.dto.AuthDtos.UpdateNameRequest;
import com.legalai.backend.web.dto.AuthDtos.UpdatePreferencesRequest;
import com.legalai.backend.web.dto.LawyerResponse;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final LawyerPreferencesService preferencesService;
    private final CurrentLawyerResolver currentLawyerResolver;
    private final boolean secureCookies;

    public AuthController(AuthService authService, LawyerPreferencesService preferencesService, CurrentLawyerResolver currentLawyerResolver,
                           @org.springframework.beans.factory.annotation.Value("${app.secure-cookies:false}") boolean secureCookies) {
        this.authService = authService;
        this.preferencesService = preferencesService;
        this.currentLawyerResolver = currentLawyerResolver;
        this.secureCookies = secureCookies;
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest body, HttpServletResponse response) {
        try {
            AuthService.AuthResult result = authService.register(body.name(), body.email(), body.password());
            setSessionCookie(response, result.rawSessionToken());
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("lawyer", LawyerResponse.from(result.lawyer())));
        } catch (AuthService.ValidationException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        } catch (AuthService.EmailTakenException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(ApiError.of("EMAIL_TAKEN", e.getMessage()));
        }
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest body, HttpServletResponse response) {
        try {
            AuthService.AuthResult result = authService.login(body.email(), body.password());
            setSessionCookie(response, result.rawSessionToken());
            return ResponseEntity.ok(Map.of("lawyer", LawyerResponse.from(result.lawyer())));
        } catch (AuthService.InvalidCredentialsException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.of("INVALID_CREDENTIALS", e.getMessage()));
        }
    }

    /** I-06: pre-auth, read-only — lets the register form hint at a taken email before submit. */
    @GetMapping("/email-available")
    public ResponseEntity<?> emailAvailable(@RequestParam String email) {
        return ResponseEntity.ok(Map.of("available", authService.isEmailAvailable(email)));
    }

    @GetMapping("/me")
    public ResponseEntity<?> me(HttpServletRequest request) {
        String raw = null;
        if (request.getCookies() != null) {
            for (Cookie c : request.getCookies()) {
                if (SessionToken.COOKIE_NAME.equals(c.getName())) raw = c.getValue();
            }
        }
        return authService.resolveSession(raw)
                .<ResponseEntity<?>>map(lawyer -> ResponseEntity.ok(Map.of("lawyer", LawyerResponse.from(lawyer))))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated()));
    }

    /** I-51: PATCH not POST — a partial update of the already-existing "current lawyer" resource. */
    @PatchMapping("/me")
    public ResponseEntity<?> updateName(@RequestBody UpdateNameRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            Lawyer updated = authService.updateName(lawyer.get().id(), body.name());
            return ResponseEntity.ok(Map.of("lawyer", LawyerResponse.from(updated)));
        } catch (InvalidLawyerException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @PostMapping("/change-password")
    public ResponseEntity<?> changePassword(@RequestBody ChangePasswordRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            authService.changePassword(lawyer.get().id(), body.currentPassword(), body.newPassword());
            return ResponseEntity.ok(Map.of());
        } catch (AuthService.IncorrectPasswordException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.of("INCORRECT_PASSWORD", e.getMessage()));
        } catch (InvalidLawyerException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    /** I-52: SD-006 — which notification types this Lawyer wants to receive. */
    @GetMapping("/me/preferences")
    public ResponseEntity<?> getPreferences(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return ResponseEntity.ok(PreferencesResponse.from(preferencesService.get(lawyer.get().id())));
    }

    @PatchMapping("/me/preferences")
    public ResponseEntity<?> updatePreferences(@RequestBody UpdatePreferencesRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return ResponseEntity.ok(PreferencesResponse.from(preferencesService.update(lawyer.get().id(), body.deadlineRemindersEnabled())));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(HttpServletRequest request, HttpServletResponse response) {
        String raw = null;
        if (request.getCookies() != null) {
            for (Cookie c : request.getCookies()) {
                if (SessionToken.COOKIE_NAME.equals(c.getName())) raw = c.getValue();
            }
        }
        authService.logout(raw);
        clearSessionCookie(response);
        return ResponseEntity.ok(Map.of());
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }

    private void setSessionCookie(HttpServletResponse response, String rawToken) {
        Cookie cookie = new Cookie(SessionToken.COOKIE_NAME, rawToken);
        cookie.setHttpOnly(true);
        cookie.setSecure(secureCookies);
        cookie.setPath("/");
        cookie.setMaxAge((int) SessionToken.SESSION_DURATION.getSeconds());
        cookie.setAttribute("SameSite", "Lax");
        response.addCookie(cookie);
    }

    private void clearSessionCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie(SessionToken.COOKIE_NAME, "");
        cookie.setHttpOnly(true);
        cookie.setSecure(secureCookies);
        cookie.setPath("/");
        cookie.setMaxAge(0);
        response.addCookie(cookie);
    }
}
