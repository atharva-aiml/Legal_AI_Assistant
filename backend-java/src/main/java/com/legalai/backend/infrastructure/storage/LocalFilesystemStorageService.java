package com.legalai.backend.infrastructure.storage;

import com.legalai.backend.application.document.StorageService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

/**
 * Dev/local-only implementation of SD-008's StorageService (System
 * Architecture §6) — no Cloudflare R2 credentials available in this
 * environment. A future R2StorageService implements the same interface;
 * nothing above this class needs to change when that happens.
 */
@Component
public class LocalFilesystemStorageService implements StorageService {

    private final Path root;

    public LocalFilesystemStorageService(@Value("${app.storage.local-dir:./uploads}") String localDir) throws IOException {
        this.root = Path.of(localDir).toAbsolutePath().normalize();
        Files.createDirectories(root);
    }

    @Override
    public String store(String originalFileName, InputStream content) throws IOException {
        String extension = extensionOf(originalFileName);
        String key = UUID.randomUUID() + extension;
        Path target = root.resolve(key);
        Files.copy(content, target, StandardCopyOption.REPLACE_EXISTING);
        return key;
    }

    @Override
    public InputStream retrieve(String storageKey) throws IOException {
        return Files.newInputStream(root.resolve(storageKey));
    }

    @Override
    public void delete(String storageKey) throws IOException {
        Files.deleteIfExists(root.resolve(storageKey));
    }

    private static String extensionOf(String fileName) {
        int dot = fileName == null ? -1 : fileName.lastIndexOf('.');
        return dot >= 0 ? fileName.substring(dot) : "";
    }
}
