package com.legalai.backend.web.controller;

import com.legalai.backend.application.notification.NotificationService;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.NotificationDtos.NotificationResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

    private final NotificationService notificationService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public NotificationController(NotificationService notificationService, CurrentLawyerResolver currentLawyerResolver) {
        this.notificationService = notificationService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping
    public ResponseEntity<?> list(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<NotificationResponse> notifications = notificationService.list(lawyer.get().id()).stream()
                .map(NotificationResponse::from).toList();
        return ResponseEntity.ok(Map.of("notifications", notifications));
    }

    @PatchMapping("/{id}/read")
    public ResponseEntity<?> markRead(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return notificationService.markRead(lawyer.get().id(), id)
                .<ResponseEntity<?>>map(n -> ResponseEntity.ok(NotificationResponse.from(n)))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Notification not found")));
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
