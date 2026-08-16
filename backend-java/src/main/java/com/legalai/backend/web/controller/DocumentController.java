package com.legalai.backend.web.controller;

import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.application.document.DraftGenerationService;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.domain.InvalidDocumentException;
import com.legalai.backend.domain.InvalidTemplateException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.DocumentDtos.DocumentResponse;
import com.legalai.backend.web.dto.TemplateDtos.GenerateDraftRequest;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
public class DocumentController {

    private final DocumentService documentService;
    private final DraftGenerationService draftGenerationService;
    private final MatterService matterService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public DocumentController(DocumentService documentService, DraftGenerationService draftGenerationService,
                               MatterService matterService, CurrentLawyerResolver currentLawyerResolver) {
        this.documentService = documentService;
        this.draftGenerationService = draftGenerationService;
        this.matterService = matterService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping("/api/matters/{matterId}/documents")
    public ResponseEntity<?> list(@PathVariable UUID matterId, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        List<DocumentResponse> documents = documentService.list(lawyer.get().firmId(), matterId).stream()
                .map(DocumentResponse::from).toList();
        return ResponseEntity.ok(Map.of("documents", documents));
    }

    @PostMapping("/api/matters/{matterId}/documents")
    public ResponseEntity<?> upload(@PathVariable UUID matterId, @RequestParam("file") MultipartFile file, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        try {
            var created = documentService.upload(
                    matterId, lawyer.get().id(), file.getOriginalFilename(), file.getContentType(), file.getSize(), file.getInputStream());
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("documents", List.of(DocumentResponse.from(created))));
        } catch (InvalidDocumentException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(ApiError.of("UPLOAD_FAILED", "Couldn't read the uploaded file."));
        }
    }

    /** SD-007 / REQ-015: 201/400/404/502 per System Architecture §4's declared status codes for this endpoint. */
    @PostMapping("/api/matters/{matterId}/documents/generate")
    public ResponseEntity<?> generate(@PathVariable UUID matterId, @RequestBody GenerateDraftRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), matterId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        UUID templateId;
        try {
            templateId = UUID.fromString(body.template_id());
        } catch (IllegalArgumentException | NullPointerException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", "A template must be selected."));
        }

        try {
            var created = draftGenerationService.generate(lawyer.get().firmId(), matterId, lawyer.get().id(), templateId, body.fields());
            return ResponseEntity.status(HttpStatus.CREATED).body(DocumentResponse.from(created));
        } catch (InvalidTemplateException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        } catch (DraftGenerationService.DraftGenerationFailedException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(ApiError.of("GENERATION_FAILED", "Couldn't generate document — retry."));
        }
    }

    @GetMapping("/api/documents/{id}")
    public ResponseEntity<?> get(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return documentService.get(lawyer.get().firmId(), id)
                .<ResponseEntity<?>>map(d -> ResponseEntity.ok(DocumentResponse.from(d)))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Document not found")));
    }

    @GetMapping("/api/documents/{id}/download")
    public ResponseEntity<?> download(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        Optional<com.legalai.backend.domain.Document> doc = documentService.get(lawyer.get().firmId(), id);
        if (doc.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Document not found"));
        }

        Optional<InputStream> content = documentService.download(lawyer.get().firmId(), id);
        if (content.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Document not found"));
        }

        return ResponseEntity.ok()
                .contentType(org.springframework.http.MediaType.parseMediaType(doc.get().mimeType()))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + doc.get().fileName() + "\"")
                .body(new InputStreamResource(content.get()));
    }

    @DeleteMapping("/api/documents/{id}")
    public ResponseEntity<?> delete(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        boolean deleted = documentService.delete(lawyer.get().firmId(), id);
        if (!deleted) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Document not found"));
        }
        return ResponseEntity.noContent().build();
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
