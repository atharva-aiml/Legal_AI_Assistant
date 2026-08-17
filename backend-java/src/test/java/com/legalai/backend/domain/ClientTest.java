package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ClientTest {

    private final UUID firmId = UUID.randomUUID();

    @Test
    void createsAClientWithTrimmedName() {
        Client.NewClient client = Client.create(firmId, "  Acme Corp  ", "a@b.com", "555-1234", "VIP client");
        assertEquals("Acme Corp", client.name());
        assertEquals(firmId, client.firmId());
    }

    @Test
    void blankOptionalFieldsBecomeNull_notEmptyStrings() {
        Client.NewClient client = Client.create(firmId, "Acme Corp", "  ", "", null);
        assertNull(client.contactEmail());
        assertNull(client.contactPhone());
        assertNull(client.notes());
    }

    @Test
    void rejectsAClientWithNoName() {
        assertThrows(InvalidClientException.class, () -> Client.create(firmId, "   ", null, null, null));
    }

    @Test
    void rejectsAClientWithNoFirm_BR008() {
        assertThrows(InvalidClientException.class, () -> Client.create(null, "Acme Corp", null, null, null));
    }

    // --- I-17: update() ---

    @Test
    void updateReturnsTrimmedFieldsWithBlanksNormalizedToNull() {
        Client.UpdatedFields updated = Client.update("  New Name  ", "new@b.com", "  ", null);
        assertEquals("New Name", updated.name());
        assertEquals("new@b.com", updated.contactEmail());
        assertNull(updated.contactPhone());
        assertNull(updated.notes());
    }

    @Test
    void updateRejectsAnEmptyName_sameInvariantAsCreate() {
        assertThrows(InvalidClientException.class, () -> Client.update("   ", "a@b.com", null, null));
    }
}
