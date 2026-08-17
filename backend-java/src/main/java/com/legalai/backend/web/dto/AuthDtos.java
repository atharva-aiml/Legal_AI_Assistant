package com.legalai.backend.web.dto;

public class AuthDtos {
    public record RegisterRequest(String name, String email, String password) {
    }

    public record LoginRequest(String email, String password) {
    }

    public record UpdateNameRequest(String name) {
    }

    public record ChangePasswordRequest(String currentPassword, String newPassword) {
    }

    public record PreferencesResponse(boolean deadlineRemindersEnabled) {
        public static PreferencesResponse from(com.legalai.backend.domain.LawyerPreferences prefs) {
            return new PreferencesResponse(prefs.deadlineRemindersEnabled());
        }
    }

    public record UpdatePreferencesRequest(boolean deadlineRemindersEnabled) {
    }
}
