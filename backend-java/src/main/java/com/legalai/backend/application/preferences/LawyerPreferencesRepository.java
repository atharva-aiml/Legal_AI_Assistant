package com.legalai.backend.application.preferences;

import com.legalai.backend.domain.LawyerPreferences;

import java.util.Optional;
import java.util.UUID;

public interface LawyerPreferencesRepository {
    /** Empty means the Lawyer has never touched this preference — callers decide the default. */
    Optional<LawyerPreferences> findByLawyerId(UUID lawyerId);

    /** Upsert semantics: one row per Lawyer, same shape as MatterView/RecentSearch's upsert. */
    LawyerPreferences upsert(UUID lawyerId, boolean deadlineRemindersEnabled);
}
