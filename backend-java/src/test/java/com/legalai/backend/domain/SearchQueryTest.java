package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class SearchQueryTest {

    @Test
    void parsesAPlainTextQuery() {
        SearchQuery query = SearchQuery.parse("Sharma", null, null, null);
        assertEquals("Sharma", query.q());
        assertNull(query.status());
        assertNull(query.from());
        assertNull(query.to());
    }

    @Test
    void trimsWhitespaceFromTheQuery() {
        SearchQuery query = SearchQuery.parse("  Meridian Buildtech  ", null, null, null);
        assertEquals("Meridian Buildtech", query.q());
    }

    @Test
    void blankQueryIsTreatedAsNoQuery_REQ011() {
        SearchQuery query = SearchQuery.parse("   ", "open", null, null);
        assertNull(query.q());
        assertEquals(MatterStatus.open, query.status());
    }

    @Test
    void parsesAStatusFilterAlone_REQ011() {
        SearchQuery query = SearchQuery.parse(null, "closed", null, null);
        assertEquals(MatterStatus.closed, query.status());
    }

    @Test
    void rejectsAnUnknownStatus() {
        assertThrows(InvalidSearchException.class, () -> SearchQuery.parse(null, "archived", null, null));
    }

    @Test
    void parsesADateRangeAlone_REQ011() {
        LocalDate from = LocalDate.of(2026, 1, 1);
        LocalDate to = LocalDate.of(2026, 12, 31);
        SearchQuery query = SearchQuery.parse(null, null, from, to);
        assertEquals(from, query.from());
        assertEquals(to, query.to());
    }

    @Test
    void rejectsADateRangeWhereStartIsAfterEnd() {
        assertThrows(InvalidSearchException.class,
                () -> SearchQuery.parse(null, null, LocalDate.of(2026, 12, 31), LocalDate.of(2026, 1, 1)));
    }

    @Test
    void rejectsASearchWithNoCriteriaAtAll() {
        assertThrows(InvalidSearchException.class, () -> SearchQuery.parse(null, null, null, null));
        assertThrows(InvalidSearchException.class, () -> SearchQuery.parse("   ", null, null, null));
    }

    @Test
    void combinesQueryStatusAndDateTogether() {
        LocalDate from = LocalDate.of(2026, 1, 1);
        SearchQuery query = SearchQuery.parse("Sharma", "open", from, null);
        assertEquals("Sharma", query.q());
        assertEquals(MatterStatus.open, query.status());
        assertEquals(from, query.from());
    }
}
