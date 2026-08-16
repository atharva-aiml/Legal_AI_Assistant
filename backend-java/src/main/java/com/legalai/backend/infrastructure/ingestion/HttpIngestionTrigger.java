package com.legalai.backend.infrastructure.ingestion;

import com.legalai.backend.application.document.DocumentRepository;
import com.legalai.backend.domain.DocumentStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;

import com.legalai.backend.application.document.IngestionTrigger;

/**
 * Java -> Python hand-off (System Architecture §6): a direct HTTP call,
 * fired without blocking the upload response. If Python can't even be
 * reached (connection-level failure), THIS class is responsible for
 * marking the Document 'failed' — Python marks it 'failed' itself for any
 * failure that happens after the request actually lands (§7: no failure
 * is invisible, even without a durable retry queue yet).
 */
@Component
public class HttpIngestionTrigger implements IngestionTrigger {

    private static final Logger log = LoggerFactory.getLogger(HttpIngestionTrigger.class);

    private final String pythonBaseUrl;
    private final DocumentRepository documentRepository;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    public HttpIngestionTrigger(
            @Value("${app.python-api-url:http://localhost:8000}") String pythonBaseUrl,
            DocumentRepository documentRepository) {
        this.pythonBaseUrl = pythonBaseUrl;
        this.documentRepository = documentRepository;
    }

    @Override
    public void triggerIngestion(UUID documentId) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(pythonBaseUrl + "/ingest/" + documentId))
                .timeout(Duration.ofSeconds(120))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        CompletableFuture
                .supplyAsync(() -> {
                    try {
                        return client.send(request, HttpResponse.BodyHandlers.ofString());
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }, Executors.newVirtualThreadPerTaskExecutor())
                .whenComplete((response, error) -> {
                    if (error != null) {
                        log.error("Ingestion service unreachable for document {}: {}", documentId, error.toString());
                        documentRepository.updateStatus(documentId, DocumentStatus.failed, "Ingestion service unreachable — retry by re-uploading.");
                    } else if (response.statusCode() >= 300) {
                        log.error("Ingestion request for document {} failed with status {}", documentId, response.statusCode());
                        documentRepository.updateStatus(documentId, DocumentStatus.failed, "Document processing failed — retry by re-uploading.");
                    }
                    // 2xx: Python itself already set status='ready' (or 'failed' with its own message) directly.
                });
    }
}
