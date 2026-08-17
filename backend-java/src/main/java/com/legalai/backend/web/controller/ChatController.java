package com.legalai.backend.web.controller;

import com.legalai.backend.application.chat.ChatService;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Optional;
import java.util.UUID;

@RestController
public class ChatController {

    private final ChatService chatService;
    private final MatterService matterService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public ChatController(ChatService chatService, MatterService matterService, CurrentLawyerResolver currentLawyerResolver) {
        this.chatService = chatService;
        this.matterService = matterService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping("/api/matters/{matterId}/chat")
    public ResponseEntity<?> history(@PathVariable UUID matterId, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        try {
            return ResponseEntity.ok(chatService.history(matterId));
        } catch (ChatService.AssistantUnavailableException e) {
            return assistantUnavailable();
        }
    }

    @PostMapping("/api/matters/{matterId}/chat")
    public ResponseEntity<?> ask(@PathVariable UUID matterId, @RequestBody AskRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }
        if (body.question() == null || body.question().isBlank()) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", "question is required"));
        }

        try {
            return ResponseEntity.ok(chatService.ask(matterId, lawyer.get().id(), body.question()));
        } catch (ChatService.NoReadyDocumentsException e) {
            return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                    .body(ApiError.of("NO_READY_DOCUMENTS", "This Matter has no ready Documents to search yet."));
        } catch (ChatService.AssistantUnavailableException e) {
            return assistantUnavailable();
        }
    }

    @PatchMapping("/api/matters/{matterId}/chat/{messageId}/pin")
    public ResponseEntity<?> togglePin(@PathVariable UUID matterId, @PathVariable UUID messageId, @RequestBody PinRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        try {
            return ResponseEntity.ok(chatService.togglePin(matterId, messageId, body.pinned()));
        } catch (ChatService.ChatMessageNotFoundException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Chat message not found"));
        } catch (ChatService.AssistantUnavailableException e) {
            return assistantUnavailable();
        }
    }

    public record AskRequest(String question) {
    }

    public record PinRequest(boolean pinned) {
    }

    private ResponseEntity<?> assistantUnavailable() {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(ApiError.of("ASSISTANT_UNAVAILABLE", "Couldn't reach the Assistant — retry."));
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
