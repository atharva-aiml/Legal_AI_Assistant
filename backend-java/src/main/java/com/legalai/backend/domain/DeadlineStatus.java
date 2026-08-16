package com.legalai.backend.domain;

/**
 * Deliberately lowercase constant names, matching MatterStatus/DocumentStatus
 * — java.lang.Enum#name() must return exactly "open"/"complete" to line up
 * with Postgres's native `deadline_status` enum labels byte-for-byte.
 */
public enum DeadlineStatus {
    open, complete
}
