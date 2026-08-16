package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class DocumentTest {

    private final UUID matterId = UUID.randomUUID();
    private final UUID lawyerId = UUID.randomUUID();

    @Test
    void createsADocumentReadyToBeStored() {
        Document.NewDocument doc = Document.create(matterId, lawyerId, "lease.pdf", "docs/abc123", "application/pdf", 2048);
        assertEquals(matterId, doc.matterId());
        assertEquals("lease.pdf", doc.fileName());
        assertEquals("application/pdf", doc.mimeType());
    }

    @Test
    void rejectsADocumentWithNoMatter_BR002() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.create(null, lawyerId, "lease.pdf", "docs/abc123", "application/pdf", 2048));
    }

    @Test
    void rejectsAnUnsupportedMimeType_REQ003() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.create(matterId, lawyerId, "malware.exe", "docs/abc123", "application/x-msdownload", 2048));
    }

    @Test
    void acceptsAllThreeDocumentedFileFamilies_REQ003() {
        assertDoesNotThrow(() -> Document.create(matterId, lawyerId, "a.pdf", "k1", "application/pdf", 10));
        assertDoesNotThrow(() -> Document.create(matterId, lawyerId, "a.docx",
                "k2", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 10));
        assertDoesNotThrow(() -> Document.create(matterId, lawyerId, "scan.png", "k3", "image/png", 10));
    }

    @Test
    void rejectsAnEmptyFile() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.create(matterId, lawyerId, "empty.pdf", "docs/abc123", "application/pdf", 0));
    }

    @Test
    void rejectsAMissingFileName() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.create(matterId, lawyerId, "   ", "docs/abc123", "application/pdf", 2048));
    }

    // --- SD-007: generated drafts ---

    private final UUID templateId = UUID.randomUUID();

    @Test
    void createsADraftDocumentNotSubjectToTheUploadMimeAllowList_REQ015() {
        Document.NewDraftDocument draft = Document.createDraft(matterId, lawyerId, "NDA.txt", "docs/draft1", "text/plain", 512, templateId);
        assertEquals(matterId, draft.matterId());
        assertEquals("text/plain", draft.mimeType());
        assertEquals(templateId, draft.sourceTemplateId());
    }

    @Test
    void rejectsADraftWithNoMatter_BR002() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.createDraft(null, lawyerId, "NDA.txt", "docs/draft1", "text/plain", 512, templateId));
    }

    @Test
    void rejectsADraftWithNoSourceTemplate() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.createDraft(matterId, lawyerId, "NDA.txt", "docs/draft1", "text/plain", 512, null));
    }

    @Test
    void rejectsADraftWithEmptyContent() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.createDraft(matterId, lawyerId, "NDA.txt", "docs/draft1", "text/plain", 0, templateId));
    }

    @Test
    void rejectsADraftWithNoStorageKey() {
        assertThrows(InvalidDocumentException.class,
                () -> Document.createDraft(matterId, lawyerId, "NDA.txt", "  ", "text/plain", 512, templateId));
    }
}
