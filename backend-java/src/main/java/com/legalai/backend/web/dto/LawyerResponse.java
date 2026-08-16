package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Lawyer;

import java.util.UUID;

/** Never includes passwordHash — mirrors the TS API's response shape exactly. */
public record LawyerResponse(UUID id, String name, String email, String role) {
    public static LawyerResponse from(Lawyer lawyer) {
        return new LawyerResponse(lawyer.id(), lawyer.name(), lawyer.email(), lawyer.role().name());
    }
}
