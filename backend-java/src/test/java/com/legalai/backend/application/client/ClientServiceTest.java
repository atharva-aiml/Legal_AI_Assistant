package com.legalai.backend.application.client;

import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.InvalidClientException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ClientServiceTest {

    /** In-memory fake — satisfies the same ClientRepository port the real JPA-backed one does. */
    static class InMemoryClientRepository implements ClientRepository {
        final List<Client> clients = new ArrayList<>();

        @Override
        public Client create(Client.NewClient record) {
            Client client = new Client(UUID.randomUUID(), record.firmId(), record.name(), record.contactEmail(), record.contactPhone(), record.notes(), Instant.now(), Instant.now());
            clients.add(client);
            return client;
        }

        @Override
        public List<Client> listByFirm(UUID firmId) {
            return clients.stream().filter(c -> c.firmId().equals(firmId)).toList();
        }

        @Override
        public Optional<Client> findById(UUID firmId, UUID id) {
            return clients.stream().filter(c -> c.firmId().equals(firmId) && c.id().equals(id)).findFirst();
        }

        @Override
        public Optional<Client> update(UUID firmId, UUID id, String name, String contactEmail, String contactPhone, String notes) {
            for (int i = 0; i < clients.size(); i++) {
                Client c = clients.get(i);
                if (c.firmId().equals(firmId) && c.id().equals(id)) {
                    Client updated = new Client(c.id(), c.firmId(), name, contactEmail, contactPhone, notes, c.createdAt(), Instant.now());
                    clients.set(i, updated);
                    return Optional.of(updated);
                }
            }
            return Optional.empty();
        }
    }

    private InMemoryClientRepository repo;
    private ClientService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryClientRepository();
        service = new ClientService(repo);
    }

    @Test
    void updatesAClientsFields() {
        Client created = service.create(firm1, "Old Name", "old@b.com", null, null);
        Client updated = service.update(firm1, created.id(), "New Name", "new@b.com", "555-0001", "Updated notes").orElseThrow();

        assertEquals("New Name", updated.name());
        assertEquals("new@b.com", updated.contactEmail());
        assertEquals("555-0001", updated.contactPhone());
        assertEquals("Updated notes", updated.notes());
    }

    @Test
    void updatePersistsInTheRepository_notJustTheReturnedValue() {
        Client created = service.create(firm1, "Old Name", null, null, null);
        service.update(firm1, created.id(), "New Name", null, null, null);

        assertEquals("New Name", service.get(firm1, created.id()).orElseThrow().name());
    }

    @Test
    void rejectsUpdatingToAnEmptyName_beforeEverTouchingTheRepository() {
        Client created = service.create(firm1, "Old Name", null, null, null);
        assertThrows(InvalidClientException.class, () -> service.update(firm1, created.id(), "   ", null, null, null));

        assertEquals("Old Name", service.get(firm1, created.id()).orElseThrow().name());
    }

    @Test
    void updatingAClientOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Client created = service.create(firm1, "Private Client", null, null, null);
        assertTrue(service.update(firm2, created.id(), "Hijacked Name", null, null, null).isEmpty());
        assertEquals("Private Client", service.get(firm1, created.id()).orElseThrow().name());
    }
}
