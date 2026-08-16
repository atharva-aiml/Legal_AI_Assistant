package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.document.DocumentRepository;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.infrastructure.persistence.entity.DocumentEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaDocumentRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class DocumentRepositoryImpl implements DocumentRepository {

    private final JpaDocumentRepository jpa;

    public DocumentRepositoryImpl(JpaDocumentRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Document create(Document.NewDocument record) {
        DocumentEntity entity = new DocumentEntity();
        entity.setId(UUID.randomUUID());
        entity.setMatterId(record.matterId());
        entity.setUploadedBy(record.uploadedBy());
        entity.setFileName(record.fileName());
        entity.setStorageKey(record.storageKey());
        entity.setMimeType(record.mimeType());
        entity.setSizeBytes(record.sizeBytes());
        entity.setStatus(DocumentStatus.uploading);
        entity.setDraft(false);
        entity.setCreatedAt(Instant.now());
        return toDomain(jpa.save(entity));
    }

    @Override
    public Document createDraft(Document.NewDraftDocument record) {
        DocumentEntity entity = new DocumentEntity();
        entity.setId(UUID.randomUUID());
        entity.setMatterId(record.matterId());
        entity.setUploadedBy(record.uploadedBy());
        entity.setFileName(record.fileName());
        entity.setStorageKey(record.storageKey());
        entity.setMimeType(record.mimeType());
        entity.setSizeBytes(record.sizeBytes());
        entity.setStatus(DocumentStatus.uploading);
        entity.setDraft(true);
        entity.setSourceTemplateId(record.sourceTemplateId());
        entity.setCreatedAt(Instant.now());
        return toDomain(jpa.save(entity));
    }

    @Override
    public List<Document> listByMatter(UUID firmId, UUID matterId) {
        return jpa.findByMatterIdAndFirmId(matterId, firmId).stream().map(DocumentRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Document> findById(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(DocumentRepositoryImpl::toDomain);
    }

    @Override
    public void updateStatus(UUID id, DocumentStatus status, String errorMessage) {
        jpa.findById(id).ifPresent(entity -> {
            entity.setStatus(status);
            entity.setErrorMessage(errorMessage);
            jpa.save(entity);
        });
    }

    @Override
    public boolean delete(UUID firmId, UUID id) {
        Optional<DocumentEntity> entity = jpa.findByIdAndFirmId(id, firmId);
        entity.ifPresent(jpa::delete);
        return entity.isPresent();
    }

    private static Document toDomain(DocumentEntity e) {
        return new Document(e.getId(), e.getMatterId(), e.getUploadedBy(), e.getFileName(), e.getStorageKey(),
                e.getMimeType(), e.getSizeBytes(), e.getStatus(), e.isDraft(), e.getSourceTemplateId(),
                e.getErrorMessage(), e.getCreatedAt());
    }
}
