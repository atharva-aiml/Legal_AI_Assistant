package com.legalai.backend.application.template;

import com.legalai.backend.domain.Template;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class TemplateServiceTest {

    static class InMemoryTemplateRepository implements TemplateRepository {
        final List<Template> templates = new ArrayList<>();

        @Override
        public List<Template> listAvailable(UUID firmId) {
            return templates.stream().filter(t -> t.firmId() == null || t.firmId().equals(firmId)).toList();
        }

        @Override
        public Optional<Template> findAvailable(UUID firmId, UUID id) {
            return templates.stream()
                    .filter(t -> t.id().equals(id) && (t.firmId() == null || t.firmId().equals(firmId)))
                    .findFirst();
        }
    }

    private InMemoryTemplateRepository repo;
    private TemplateService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();

    private Template template(UUID firmId, String name) {
        return new Template(UUID.randomUUID(), firmId, name, null, "body {{x}}", Instant.now());
    }

    @BeforeEach
    void setUp() {
        repo = new InMemoryTemplateRepository();
        service = new TemplateService(repo);
    }

    @Test
    void listsSystemTemplatesForAnyFirm() {
        Template system = template(null, "NDA");
        repo.templates.add(system);

        assertEquals(List.of(system), service.list(firm1));
        assertEquals(List.of(system), service.list(firm2));
    }

    @Test
    void listsAFirmsOwnCustomTemplateAlongsideSystemOnes() {
        Template system = template(null, "NDA");
        Template custom = template(firm1, "Firm 1's Custom Letter");
        repo.templates.add(system);
        repo.templates.add(custom);

        List<Template> forFirm1 = service.list(firm1);
        assertEquals(2, forFirm1.size());
        assertTrue(forFirm1.contains(system));
        assertTrue(forFirm1.contains(custom));
    }

    @Test
    void neverListsAnotherFirmsCustomTemplate_BR008() {
        Template firm1Custom = template(firm1, "Firm 1's Custom Letter");
        repo.templates.add(firm1Custom);

        assertTrue(service.list(firm2).isEmpty());
    }

    @Test
    void getReturnsASystemTemplateForAnyFirm() {
        Template system = template(null, "NDA");
        repo.templates.add(system);

        assertEquals(Optional.of(system), service.get(firm2, system.id()));
    }

    @Test
    void getReturnsEmptyForAnotherFirmsCustomTemplate_BR008() {
        Template firm1Custom = template(firm1, "Firm 1's Custom Letter");
        repo.templates.add(firm1Custom);

        assertTrue(service.get(firm2, firm1Custom.id()).isEmpty());
    }
}
