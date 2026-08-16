package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class TemplateTest {

    private final UUID firmId = UUID.randomUUID();

    @Test
    void createsATemplate() {
        Template.NewTemplate t = Template.create(firmId, "NDA", "Mutual NDA", "Hello {{name}}");
        assertEquals(firmId, t.firmId());
        assertEquals("NDA", t.name());
        assertEquals("Mutual NDA", t.description());
        assertEquals("Hello {{name}}", t.body());
    }

    @Test
    void allowsANullFirmIdForASystemTemplate() {
        Template.NewTemplate t = Template.create(null, "NDA", null, "Hello {{name}}");
        assertNull(t.firmId());
    }

    @Test
    void trimsNameAndBody() {
        Template.NewTemplate t = Template.create(firmId, "  NDA  ", null, "  Hello {{name}}  ");
        assertEquals("NDA", t.name());
        assertEquals("Hello {{name}}", t.body());
    }

    @Test
    void blankDescriptionBecomesNull() {
        Template.NewTemplate t = Template.create(firmId, "NDA", "   ", "body");
        assertNull(t.description());
    }

    @Test
    void rejectsABlankName() {
        assertThrows(InvalidTemplateException.class, () -> Template.create(firmId, "   ", null, "body"));
    }

    @Test
    void rejectsBlankBody() {
        assertThrows(InvalidTemplateException.class, () -> Template.create(firmId, "NDA", null, "   "));
    }

    private Template template(String body) {
        return new Template(UUID.randomUUID(), firmId, "NDA", null, body, Instant.now());
    }

    @Test
    void placeholdersExtractsDistinctNamesInFirstAppearanceOrder() {
        Template t = template("Dear {{counterparty_name}}, re: {{matter_title}}. Regards, {{counterparty_name}}.");
        assertEquals(List.of("counterparty_name", "matter_title"), List.copyOf(t.placeholders()));
    }

    @Test
    void placeholdersIsEmptyWhenBodyHasNone() {
        Template t = template("No placeholders here.");
        assertTrue(t.placeholders().isEmpty());
    }

    @Test
    void rendersAllPlaceholdersWithSuppliedValues_REQ015() {
        Template t = template("Dear {{counterparty_name}}, this concerns {{matter_title}}.");
        String rendered = t.render(Map.of("counterparty_name", "Northgate Logistics", "matter_title", "Vasquez v. Northgate"));
        assertEquals("Dear Northgate Logistics, this concerns Vasquez v. Northgate.", rendered);
    }

    @Test
    void repeatedPlaceholdersAreAllSubstituted() {
        Template t = template("{{name}} agrees that {{name}} will comply.");
        assertEquals("Acme agrees that Acme will comply.", t.render(Map.of("name", "Acme")));
    }

    @Test
    void rendersBodyUnchangedWhenThereAreNoPlaceholders() {
        Template t = template("Plain text, no placeholders.");
        assertEquals("Plain text, no placeholders.", t.render(Map.of()));
    }

    @Test
    void rejectsRenderingWhenAPlaceholderHasNoValueAtAll() {
        Template t = template("Dear {{counterparty_name}}.");
        InvalidTemplateException e = assertThrows(InvalidTemplateException.class, () -> t.render(Map.of()));
        assertTrue(e.getMessage().contains("counterparty_name"));
    }

    @Test
    void rejectsRenderingWhenAPlaceholderValueIsBlank() {
        Template t = template("Dear {{counterparty_name}}.");
        assertThrows(InvalidTemplateException.class, () -> t.render(Map.of("counterparty_name", "   ")));
    }

    @Test
    void rejectsRenderingWithANullFieldsMap() {
        Template t = template("Dear {{counterparty_name}}.");
        assertThrows(InvalidTemplateException.class, () -> t.render(null));
    }
}
