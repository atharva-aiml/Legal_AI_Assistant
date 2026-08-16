package com.legalai.backend.application.document;

import java.util.UUID;

/**
 * Port over the Java -> Python hand-off (System Architecture §6). Fire-and
 * -forget: DocumentService calls this after a Document is stored, but does
 * not wait for ingestion to finish before responding to the browser.
 */
public interface IngestionTrigger {
    void triggerIngestion(UUID documentId);
}
