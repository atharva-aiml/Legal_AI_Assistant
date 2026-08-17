package com.legalai.backend.domain;

/**
 * I-40. Deliberately lowercase constant names, matching DeadlineStatus/
 * MatterStatus — java.lang.Enum#name() must return exactly "standard"/
 * "critical" to line up with Postgres's native `deadline_priority` enum
 * labels byte-for-byte.
 */
public enum DeadlinePriority {
    standard, critical
}
