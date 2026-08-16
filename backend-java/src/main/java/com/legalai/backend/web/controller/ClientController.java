package com.legalai.backend.web.controller;

import com.legalai.backend.application.client.ClientService;
import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.InvalidClientException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.ClientDtos.ClientResponse;
import com.legalai.backend.web.dto.ClientDtos.CreateClientRequest;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
@RequestMapping("/api/clients")
public class ClientController {

    private final ClientService clientService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public ClientController(ClientService clientService, CurrentLawyerResolver currentLawyerResolver) {
        this.clientService = clientService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    @GetMapping
    public ResponseEntity<?> list(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<ClientResponse> clients = clientService.list(lawyer.get().firmId()).stream().map(ClientResponse::from).toList();
        return ResponseEntity.ok(Map.of("clients", clients));
    }

    @PostMapping
    public ResponseEntity<?> create(@RequestBody CreateClientRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            Client created = clientService.create(lawyer.get().firmId(), body.name(), body.contact_email(), body.contact_phone(), body.notes());
            return ResponseEntity.status(HttpStatus.CREATED).body(ClientResponse.from(created));
        } catch (InvalidClientException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        return clientService.get(lawyer.get().firmId(), id)
                .<ResponseEntity<?>>map(c -> ResponseEntity.ok(Map.of("client", ClientResponse.from(c))))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Client not found")));
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
