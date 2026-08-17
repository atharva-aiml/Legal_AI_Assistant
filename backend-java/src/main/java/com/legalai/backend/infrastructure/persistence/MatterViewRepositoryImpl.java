package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.matterview.MatterViewRepository;
import com.legalai.backend.domain.MatterView;
import com.legalai.backend.infrastructure.persistence.entity.MatterViewEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaMatterViewRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/** Real MatterViewRepository, backed by Postgres via Spring Data JPA. */
@Repository
public class MatterViewRepositoryImpl implements MatterViewRepository {

    private final JpaMatterViewRepository jpa;

    public MatterViewRepositoryImpl(JpaMatterViewRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    @Transactional
    public void recordView(UUID lawyerId, UUID matterId) {
        jpa.upsertView(lawyerId, matterId);
    }

    @Override
    public List<MatterView> listRecentlyViewed(UUID lawyerId, int limit) {
        return jpa.findByLawyerIdOrderByViewedAtDesc(lawyerId, PageRequest.of(0, limit))
                .stream()
                .map(MatterViewRepositoryImpl::toDomain)
                .toList();
    }

    private static MatterView toDomain(MatterViewEntity e) {
        return new MatterView(e.getLawyerId(), e.getMatterId(), e.getViewedAt());
    }
}
