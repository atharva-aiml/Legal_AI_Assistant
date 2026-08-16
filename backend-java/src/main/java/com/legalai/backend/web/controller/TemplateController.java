package com.legalai.backend.web.controller;

import com.legalai.backend.application.template.TemplateService;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.TemplateDtos.TemplateResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/templates")
public class TemplateController {

    private final TemplateService templateService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public TemplateController(TemplateService templateService, CurrentLawyerResolver currentLawyerResolver) {
        this.templateService = templateService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    /** SD-007 / REQ-015: system Templates plus this Firm's own, per System Architecture §7's "cached until the next Template write" note — no writes exist yet, so nothing to invalidate. */
    @GetMapping
    public ResponseEntity<?> list(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<TemplateResponse> templates = templateService.list(lawyer.get().firmId()).stream()
                .map(TemplateResponse::from).toList();
        return ResponseEntity.ok(Map.of("templates", templates));
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
