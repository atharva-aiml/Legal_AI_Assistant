package com.legalai.backend.web.controller;

import com.legalai.backend.application.activity.ActivityService;
import com.legalai.backend.application.client.ClientService;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.application.matterview.MatterViewService;
import com.legalai.backend.domain.InvalidMatterException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.domain.MatterStatus;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.ActivityDtos.ActivityEntryResponse;
import com.legalai.backend.web.dto.ClientDtos.ClientResponse;
import com.legalai.backend.web.dto.MatterDtos.CreateMatterRequest;
import com.legalai.backend.web.dto.MatterDtos.MatterResponse;
import com.legalai.backend.web.dto.MatterDtos.OpenDeadlinesError;
import com.legalai.backend.web.dto.MatterDtos.RenameMatterRequest;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
@RequestMapping("/api/matters")
public class MatterController {

    private final MatterService matterService;
    private final ClientService clientService;
    private final MatterViewService matterViewService;
    private final ActivityService activityService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public MatterController(MatterService matterService, ClientService clientService, MatterViewService matterViewService, ActivityService activityService, CurrentLawyerResolver currentLawyerResolver) {
        this.matterService = matterService;
        this.clientService = clientService;
        this.matterViewService = matterViewService;
        this.activityService = activityService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    /** I-07: "recent" is a fixed dashboard-widget list — must be matched above /{id} or "recent" would be parsed as a Matter UUID. */
    @GetMapping("/recent")
    public ResponseEntity<?> recent(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<MatterResponse> recent = matterViewService.listRecentlyViewed(lawyer.get().id()).stream()
                .map(view -> matterService.get(lawyer.get().firmId(), view.matterId()))
                .flatMap(Optional::stream)
                .map(MatterResponse::from)
                .toList();
        return ResponseEntity.ok(Map.of("matters", recent));
    }

    @GetMapping
    public ResponseEntity<?> list(@RequestParam(required = false) UUID clientId,
                                   @RequestParam(required = false) MatterStatus status,
                                   HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<MatterResponse> matters = matterService.list(lawyer.get().firmId(), clientId, status).stream().map(MatterResponse::from).toList();
        return ResponseEntity.ok(Map.of("matters", matters));
    }

    @PostMapping
    public ResponseEntity<?> create(@RequestBody CreateMatterRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        UUID clientId;
        try {
            clientId = body.client_id() == null ? null : UUID.fromString(body.client_id());
        } catch (IllegalArgumentException e) {
            clientId = null;
        }

        // Confirm the Client is real AND belongs to the caller's Firm before
        // creating the Matter (BR-008) — mirrors the original TS API route's
        // explicit ownership check, done here rather than in MatterService
        // since it's a cross-entity authorization concern, not a Matter
        // domain rule.
        if (clientId != null && clientService.get(lawyer.get().firmId(), clientId).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Client not found"));
        }

        try {
            Matter created = matterService.create(lawyer.get().firmId(), clientId, body.title());
            return ResponseEntity.status(HttpStatus.CREATED).body(MatterResponse.from(created));
        } catch (InvalidMatterException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        Optional<Matter> matter = matterService.get(lawyer.get().firmId(), id);
        if (matter.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        Optional<ClientResponse> client = clientService.get(lawyer.get().firmId(), matter.get().clientId()).map(ClientResponse::from);
        return ResponseEntity.ok(Map.of("matter", MatterResponse.from(matter.get()), "client", client.orElse(null)));
    }

    /** I-07: separate from `get` (a plain read) so opening the Matter Detail page has one explicit, idempotent write to attribute the view to. */
    @PostMapping("/{id}/view")
    public ResponseEntity<?> recordView(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        if (matterService.get(lawyer.get().firmId(), id).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }
        matterViewService.recordView(lawyer.get().id(), id);
        return ResponseEntity.ok(Map.of());
    }

    /** I-32: read-only merge of Documents/Deadlines (Java-owned) and Chat questions (Python-owned, via the same proxy the Chat panel already uses). */
    @GetMapping("/{id}/activity")
    public ResponseEntity<?> activity(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();
        if (matterService.get(lawyer.get().firmId(), id).isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found"));
        }

        List<ActivityEntryResponse> entries = activityService.forMatter(lawyer.get().firmId(), id).stream()
                .map(ActivityEntryResponse::from)
                .toList();
        return ResponseEntity.ok(Map.of("entries", entries));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<?> rename(@PathVariable UUID id, @RequestBody RenameMatterRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            return matterService.rename(lawyer.get().firmId(), id, body.title() == null ? "" : body.title())
                    .<ResponseEntity<?>>map(m -> ResponseEntity.ok(MatterResponse.from(m)))
                    .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found")));
        } catch (InvalidMatterException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @PostMapping("/{id}/close")
    public ResponseEntity<?> close(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            return matterService.close(lawyer.get().firmId(), id)
                    .<ResponseEntity<?>>map(m -> ResponseEntity.ok(MatterResponse.from(m)))
                    .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found")));
        } catch (MatterService.MatterHasOpenDeadlinesException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(OpenDeadlinesError.of(e.getMessage(), e.openDeadlines()));
        }
    }

    @PostMapping("/{id}/reopen")
    public ResponseEntity<?> reopen(@PathVariable UUID id, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            return matterService.reopen(lawyer.get().firmId(), id)
                    .<ResponseEntity<?>>map(m -> ResponseEntity.ok(MatterResponse.from(m)))
                    .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(ApiError.notFound("Matter not found")));
        } catch (InvalidMatterException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }
}
