package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class LawyerTest {

    // --- I-51: validateName() ---

    @Test
    void trimsWhitespaceFromTheName() {
        assertEquals("Jane Doe", Lawyer.validateName("  Jane Doe  "));
    }

    @Test
    void rejectsABlankName() {
        assertThrows(InvalidLawyerException.class, () -> Lawyer.validateName("   "));
    }

    @Test
    void rejectsANullName() {
        assertThrows(InvalidLawyerException.class, () -> Lawyer.validateName(null));
    }

    // --- I-51: validateNewPassword() ---

    @Test
    void acceptsAnEightCharacterPassword() {
        assertEquals("password", Lawyer.validateNewPassword("password"));
    }

    @Test
    void rejectsAPasswordShorterThanEightCharacters() {
        assertThrows(InvalidLawyerException.class, () -> Lawyer.validateNewPassword("short1"));
    }

    @Test
    void rejectsANullPassword() {
        assertThrows(InvalidLawyerException.class, () -> Lawyer.validateNewPassword(null));
    }
}
