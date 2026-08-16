package com.legalai.backend.domain;

/**
 * Deliberately lowercase constant names (against normal Java style) so
 * java.lang.Enum#name() returns exactly "open"/"closed", matching
 * Postgres's native `matter_status` enum labels byte-for-byte — verified
 * against the real database via a spike (Technology Decision Log) before
 * committing to this approach over a custom AttributeConverter.
 */
public enum MatterStatus {
    open, closed
}
