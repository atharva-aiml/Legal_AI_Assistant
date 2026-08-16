package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/** Direct port of the original TypeScript lib/domain/matter.test.ts — same cases, same intent. */
class MatterTest {

    private final UUID firmId = UUID.randomUUID();
    private final UUID clientId = UUID.randomUUID();

    @Test
    void createsAMatterWithStatusOpenByDefault() {
        Matter.NewMatter matter = Matter.create(firmId, clientId, "Smith v. Jones");
        assertEquals(MatterStatus.open, matter.status());
        assertEquals("Smith v. Jones", matter.title());
        assertEquals(clientId, matter.clientId());
        assertEquals(firmId, matter.firmId());
    }

    @Test
    void trimsWhitespaceFromTheTitle() {
        Matter.NewMatter matter = Matter.create(firmId, clientId, "  Padded Title  ");
        assertEquals("Padded Title", matter.title());
    }

    @Test
    void rejectsAMatterWithNoTitle() {
        assertThrows(InvalidMatterException.class, () -> Matter.create(firmId, clientId, "   "));
    }

    @Test
    void rejectsAMatterWithNoClient_BR001() {
        assertThrows(InvalidMatterException.class, () -> Matter.create(firmId, null, "Orphan Matter"));
    }

    @Test
    void rejectsAMatterWithNoFirm_BR008() {
        assertThrows(InvalidMatterException.class, () -> Matter.create(null, clientId, "Orphan Matter"));
    }

    @Test
    void renameReturnsTheTrimmedTitle() {
        assertEquals("New Title", Matter.renameTitle("  New Title  "));
    }

    @Test
    void renameRejectsAnEmptyTitle() {
        assertThrows(InvalidMatterException.class, () -> Matter.renameTitle("   "));
    }
}
