package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class RecentSearchTest {

    @Test
    void trimsWhitespaceFromTheQuery() {
        assertEquals("Acme Corp", RecentSearch.validateQuery("  Acme Corp  "));
    }

    @Test
    void rejectsABlankQuery() {
        assertThrows(InvalidSearchException.class, () -> RecentSearch.validateQuery("   "));
    }

    @Test
    void rejectsANullQuery() {
        assertThrows(InvalidSearchException.class, () -> RecentSearch.validateQuery(null));
    }
}
