package com.legalai.backend.domain;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * SD-007: a pre-authored, placeholder-bearing document template. {@code
 * firmId} is nullable — null means a system template available to every
 * Firm, a real value means a Firm-custom template visible only to that
 * Firm (System Architecture §3's ER note: "null = system template, set =
 * firm-custom"). V0.8 doesn't build a template-authoring UI ("does not
 * create templates from user free text — templates are pre-authored"), so
 * {@link #create} exists for completeness/future use, not a UI that calls
 * it yet — today's only Templates come from a one-time SQL seed.
 */
public record Template(UUID id, UUID firmId, String name, String description, String body, Instant createdAt) {

    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{\\s*([a-zA-Z0-9_]+)\\s*\\}\\}");

    public record NewTemplate(UUID firmId, String name, String description, String body) {
    }

    public static NewTemplate create(UUID firmId, String name, String description, String body) {
        String trimmedName = name == null ? "" : name.trim();
        if (trimmedName.isEmpty()) {
            throw new InvalidTemplateException("A Template name is required.");
        }
        String trimmedBody = body == null ? "" : body.trim();
        if (trimmedBody.isEmpty()) {
            throw new InvalidTemplateException("A Template must have body content.");
        }
        String trimmedDescription = description == null ? null : description.trim();
        return new NewTemplate(firmId, trimmedName, (trimmedDescription == null || trimmedDescription.isEmpty()) ? null : trimmedDescription, trimmedBody);
    }

    /** Distinct {@code {{placeholder}}} names referenced in the body, in first-appearance order. */
    public Set<String> placeholders() {
        Set<String> names = new LinkedHashSet<>();
        Matcher matcher = PLACEHOLDER.matcher(body);
        while (matcher.find()) {
            names.add(matcher.group(1));
        }
        return names;
    }

    /**
     * REQ-015: substitutes every placeholder with its supplied field
     * value. Every placeholder the body actually references must have a
     * non-blank value — a generated legal draft with a literal
     * "{{counterparty_name}}" left in it is worse than refusing to
     * generate at all, so this fails loudly and names exactly what's
     * missing rather than silently leaving gaps.
     */
    public String render(Map<String, String> fields) {
        Set<String> missing = new LinkedHashSet<>();
        for (String name : placeholders()) {
            String value = fields == null ? null : fields.get(name);
            if (value == null || value.isBlank()) {
                missing.add(name);
            }
        }
        if (!missing.isEmpty()) {
            throw new InvalidTemplateException("Missing a value for: " + String.join(", ", missing));
        }

        Matcher matcher = PLACEHOLDER.matcher(body);
        StringBuilder result = new StringBuilder();
        while (matcher.find()) {
            matcher.appendReplacement(result, Matcher.quoteReplacement(fields.get(matcher.group(1))));
        }
        matcher.appendTail(result);
        return result.toString();
    }
}
