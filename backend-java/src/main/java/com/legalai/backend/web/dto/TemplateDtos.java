package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Template;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public class TemplateDtos {
    public record TemplateResponse(
            UUID id,
            UUID firmId,
            String name,
            String description,
            List<String> placeholders,
            Instant createdAt) {
        public static TemplateResponse from(Template t) {
            return new TemplateResponse(t.id(), t.firmId(), t.name(), t.description(), t.placeholders().stream().sorted().toList(), t.createdAt());
        }
    }

    /** { template_id, fields } per System Architecture §4's declared generate-endpoint request body. */
    public record GenerateDraftRequest(String template_id, java.util.Map<String, String> fields) {
    }
}
