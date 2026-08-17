package com.legalai.backend.application.matterview;

import com.legalai.backend.domain.MatterView;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
public class MatterViewService {

    /** REQ (I-07): "recent" is a short, dashboard-widget-sized list, not a full history. */
    private static final int RECENT_LIMIT = 5;

    private final MatterViewRepository repository;

    public MatterViewService(MatterViewRepository repository) {
        this.repository = repository;
    }

    public void recordView(UUID lawyerId, UUID matterId) {
        repository.recordView(lawyerId, matterId);
    }

    public List<MatterView> listRecentlyViewed(UUID lawyerId) {
        return repository.listRecentlyViewed(lawyerId, RECENT_LIMIT);
    }
}
