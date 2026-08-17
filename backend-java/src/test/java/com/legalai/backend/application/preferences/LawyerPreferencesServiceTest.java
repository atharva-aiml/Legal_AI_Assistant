package com.legalai.backend.application.preferences;

import com.legalai.backend.domain.LawyerPreferences;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class LawyerPreferencesServiceTest {

    static class InMemoryLawyerPreferencesRepository implements LawyerPreferencesRepository {
        final Map<UUID, LawyerPreferences> byLawyer = new HashMap<>();

        @Override
        public Optional<LawyerPreferences> findByLawyerId(UUID lawyerId) {
            return Optional.ofNullable(byLawyer.get(lawyerId));
        }

        @Override
        public LawyerPreferences upsert(UUID lawyerId, boolean deadlineRemindersEnabled) {
            LawyerPreferences updated = new LawyerPreferences(lawyerId, deadlineRemindersEnabled);
            byLawyer.put(lawyerId, updated);
            return updated;
        }
    }

    private InMemoryLawyerPreferencesRepository repo;
    private LawyerPreferencesService service;
    private final UUID lawyer1 = UUID.randomUUID();
    private final UUID lawyer2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryLawyerPreferencesRepository();
        service = new LawyerPreferencesService(repo);
    }

    @Test
    void aLawyerWhoHasNeverSetPreferencesGetsTheEnabledDefault() {
        LawyerPreferences prefs = service.get(lawyer1);
        assertTrue(prefs.deadlineRemindersEnabled());
    }

    @Test
    void updatingPersistsTheNewValue() {
        service.update(lawyer1, false);
        assertFalse(service.get(lawyer1).deadlineRemindersEnabled());
    }

    @Test
    void updatingCanTurnThePreferenceBackOn() {
        service.update(lawyer1, false);
        service.update(lawyer1, true);
        assertTrue(service.get(lawyer1).deadlineRemindersEnabled());
    }

    @Test
    void oneLawyersPreferenceNeverLeaksIntoAnothers() {
        service.update(lawyer1, false);
        assertTrue(service.get(lawyer2).deadlineRemindersEnabled(), "lawyer2 never touched their preference, so it stays at the default");
    }
}
