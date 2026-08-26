package com.legalai.backend.application.matterview;

import com.legalai.backend.domain.MatterView;

import java.util.List;
import java.util.UUID;

public interface MatterViewRepository {
    /** Upsert semantics: viewing an already-viewed Matter again updates its timestamp, never adds a second row. */
    void recordView(UUID lawyerId, UUID matterId);

    /** Most-recently-viewed first, capped at limit. */
    List<MatterView> listRecentlyViewed(UUID lawyerId, int limit);

    /** Cascade-delete only — caller (ClientService.deleteCascade) has already verified Matter ownership. */
    void deleteByMatter(UUID matterId);
}
