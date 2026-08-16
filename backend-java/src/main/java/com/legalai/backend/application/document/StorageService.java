package com.legalai.backend.application.document;

import java.io.InputStream;

/**
 * Port (SD-008). `LocalFilesystemStorageService` implements this in dev
 * (no R2 credentials available — System Architecture §6); a future
 * `R2StorageService` implements the same interface for production.
 */
public interface StorageService {
    /** Stores the bytes under a new, unique key and returns that key. */
    String store(String originalFileName, InputStream content) throws java.io.IOException;

    InputStream retrieve(String storageKey) throws java.io.IOException;

    /** REQ-027. No-op (not an error) if the key is already gone — deletion is idempotent. */
    void delete(String storageKey) throws java.io.IOException;
}
