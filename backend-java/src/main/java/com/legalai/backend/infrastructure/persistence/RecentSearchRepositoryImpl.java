package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.recentsearch.RecentSearchRepository;
import com.legalai.backend.domain.RecentSearch;
import com.legalai.backend.infrastructure.persistence.entity.RecentSearchEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaRecentSearchRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/** Real RecentSearchRepository, backed by Postgres via Spring Data JPA. */
@Repository
public class RecentSearchRepositoryImpl implements RecentSearchRepository {

    private final JpaRecentSearchRepository jpa;

    public RecentSearchRepositoryImpl(JpaRecentSearchRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    @Transactional
    public void record(UUID lawyerId, String query) {
        jpa.upsertSearch(lawyerId, query);
    }

    @Override
    public List<RecentSearch> listRecent(UUID lawyerId, int limit) {
        return jpa.findByLawyerIdOrderBySearchedAtDesc(lawyerId, PageRequest.of(0, limit))
                .stream()
                .map(RecentSearchRepositoryImpl::toDomain)
                .toList();
    }

    private static RecentSearch toDomain(RecentSearchEntity e) {
        return new RecentSearch(e.getLawyerId(), e.getQuery(), e.getSearchedAt());
    }
}
