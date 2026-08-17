package com.legalai.backend.application.preferences;

import com.legalai.backend.domain.LawyerPreferences;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class LawyerPreferencesService {

    private final LawyerPreferencesRepository repository;

    public LawyerPreferencesService(LawyerPreferencesRepository repository) {
        this.repository = repository;
    }

    public LawyerPreferences get(UUID lawyerId) {
        return repository.findByLawyerId(lawyerId).orElseGet(() -> LawyerPreferences.defaultFor(lawyerId));
    }

    public LawyerPreferences update(UUID lawyerId, boolean deadlineRemindersEnabled) {
        return repository.upsert(lawyerId, deadlineRemindersEnabled);
    }
}
