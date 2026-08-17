package com.legalai.backend.web.controller;

import com.legalai.backend.application.deadline.DeadlineService;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.InvalidDeadlineException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.DeadlineDtos.CreateDeadlineRequest;
import com.legalai.backend.web.dto.DeadlineDtos.DeadlineResponse;
import com.legalai.backend.web.dto.DeadlineDtos.UpdateDeadlineRequest;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
public class DeadlineController {

    private final DeadlineService deadlineService;
    private final MatterService matterService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public DeadlineController(DeadlineService deadlineService, MatterService matterService, CurrentLawyerResolver currentLawyerResolver) {
        this.deadlineService = deadlineService;
        this.matterService = matterService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping("/api/matters/{matterId}/deadlines")
    public ResponseEntity<?> list(@PathVariable UUID matterId, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        List<DeadlineResponse> deadlines = deadlineService.list(lawyer.get().firmId(), matterId).stream()
                .map(DeadlineResponse::from).toList();
        return ResponseEntity.ok(Map.of("deadlines", deadlines));
    }

    @PostMapping("/api/matters/{matterId}/deadlines")
    public ResponseEntity<?> create(@PathVariable UUID matterId, @RequestBody CreateDeadlineRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        DeadlinePriority priority;
        try {
            priority = body.priority() == null ? null : DeadlinePriority.valueOf(body.priority());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", "Unknown Deadline priority: " + body.priority()));
        }

        try {
            Deadline created = deadlineService.create(matterId, body.title(), body.dueDate(), priority, body.notificationLeadDays());
            return ResponseEntity.status(HttpStatus.CREATED).body(DeadlineResponse.from(created));
        } catch (InvalidDeadlineException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @GetMapping("/api/deadlines/{id}")
    public ResponseEntity<?> get(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return deadlineService.get(lawyer.get().firmId(), id)
                .<ResponseEntity<?>>map(d -> ResponseEntity.ok(DeadlineResponse.from(d)))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Deadline not found")));
    }

    @GetMapping("/api/deadlines/upcoming")
    public ResponseEntity<?> upcoming(@RequestParam(required = false, defaultValue = "7") int days, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<DeadlineResponse> deadlines = deadlineService.upcoming(lawyer.get().firmId(), days).stream()
                .map(DeadlineResponse::from).toList();
        return ResponseEntity.ok(Map.of("deadlines", deadlines));
    }

    @PatchMapping("/api/deadlines/{id}")
    public ResponseEntity<?> update(@PathVariable UUID id, @RequestBody UpdateDeadlineRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        DeadlineStatus status;
        try {
            status = body.status() == null ? null : DeadlineStatus.valueOf(body.status());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", "Unknown Deadline status: " + body.status()));
        }

        DeadlinePriority priority;
        try {
            priority = body.priority() == null ? null : DeadlinePriority.valueOf(body.priority());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", "Unknown Deadline priority: " + body.priority()));
        }

        try {
            return deadlineService.update(lawyer.get().firmId(), id, body.title(), body.dueDate(), status, priority, body.notificationLeadDays())
                    .<ResponseEntity<?>>map(d -> ResponseEntity.ok(DeadlineResponse.from(d)))
                    .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Deadline not found")));
        } catch (InvalidDeadlineException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
