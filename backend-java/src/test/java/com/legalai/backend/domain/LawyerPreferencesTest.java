package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class LawyerPreferencesTest {

    @Test
    void defaultsToDeadlineRemindersEnabled_preservesPreI52Behavior() {
        UUID lawyerId = UUID.randomUUID();
        LawyerPreferences prefs = LawyerPreferences.defaultFor(lawyerId);

        assertEquals(lawyerId, prefs.lawyerId());
        assertTrue(prefs.deadlineRemindersEnabled());
    }

    @Test
    void rejectsPreferencesWithNoLawyer() {
        assertThrows(InvalidLawyerException.class, () -> LawyerPreferences.defaultFor(null));
    }
}
