package com.legalai.backend.domain;

import java.util.UUID;

/**
 * I-52: a per-Lawyer notification preference. Deadline reminders are the
 * only notification type that exists today (SD-006), so a single boolean
 * is the honest shape — a multi-type preferences map would be speculative
 * until a second notification type actually exists.
 */
public record LawyerPreferences(UUID lawyerId, boolean deadlineRemindersEnabled) {

    /**
     * Before I-52, every Lawyer in a Firm received every Deadline reminder
     * with no way to opt out — a Lawyer who has never touched this setting
     * must keep getting reminders exactly as before, so "no preference row
     * yet" defaults to enabled, not disabled.
     */
    public static LawyerPreferences defaultFor(UUID lawyerId) {
        if (lawyerId == null) {
            throw new InvalidLawyerException("Preferences must belong to a real Lawyer.");
        }
        return new LawyerPreferences(lawyerId, true);
    }
}
