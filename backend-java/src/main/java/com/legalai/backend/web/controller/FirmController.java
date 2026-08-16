package com.legalai.backend.web.controller;

import com.legalai.backend.application.auth.AuthService;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.LawyerResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/** SCR-15: read-only Firm/team roster. Invite/remove is Build Plan V0.7, not built yet. */
@RestController
@RequestMapping("/api/firm")
public class FirmController {

    private final AuthService authService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public FirmController(AuthService authService, CurrentLawyerResolver currentLawyerResolver) {
        this.authService = authService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping("/lawyers")
    public ResponseEntity<?> listLawyers(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());

        List<LawyerResponse> lawyers = authService.listFirmMembers(lawyer.get().firmId()).stream()
                .map(LawyerResponse::from).toList();
        return ResponseEntity.ok(Map.of("lawyers", lawyers));
    }
}
