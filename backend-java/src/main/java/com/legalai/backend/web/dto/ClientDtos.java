package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Client;

import java.time.Instant;
import java.util.UUID;

public class ClientDtos {
    public record CreateClientRequest(String name, String contact_email, String contact_phone, String notes) {
    }

    public record ClientResponse(
            UUID id,
            UUID firmId,
            String name,
            String contactEmail,
            String contactPhone,
            String notes,
            Instant createdAt,
            Instant updatedAt) {
        public static ClientResponse from(Client c) {
            return new ClientResponse(c.id(), c.firmId(), c.name(), c.contactEmail(), c.contactPhone(), c.notes(), c.createdAt(), c.updatedAt());
        }
    }
}
