package com.legalai.backend.infrastructure.chat;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatGateway;
import com.legalai.backend.application.chat.ChatService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import java.util.UUID;

/**
 * Java -> Python hand-off for chat (System Architecture §6). Unlike
 * {@code HttpIngestionTrigger}'s fire-and-forget, this call blocks: the
 * browser is waiting on an answer, so Java waits on Python's response and
 * relays it rather than acknowledging immediately.
 */
@Component
public class HttpChatGateway implements ChatGateway {

    private final String pythonBaseUrl;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    private final ObjectMapper mapper = new ObjectMapper(); // Jackson 3 (Spring Boot 4): java.time support is built into jackson-databind, no separate JavaTimeModule needed

    public HttpChatGateway(@Value("${app.python-api-url:http://localhost:8000}") String pythonBaseUrl) {
        this.pythonBaseUrl = pythonBaseUrl;
    }

    @Override
    public ChatMessageDto ask(UUID matterId, UUID lawyerId, String question) {
        try {
            String requestBody = mapper.writeValueAsString(Map.of("lawyerId", lawyerId.toString(), "question", question));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(pythonBaseUrl + "/chat/" + matterId))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 422) {
                throw new ChatService.NoReadyDocumentsException();
            }
            if (response.statusCode() >= 300) {
                throw new ChatService.AssistantUnavailableException("Assistant service returned " + response.statusCode());
            }
            return mapper.readValue(response.body(), ChatMessageDto.class);
        } catch (IOException e) {
            throw new ChatService.AssistantUnavailableException("Assistant service unreachable", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ChatService.AssistantUnavailableException("Assistant call interrupted", e);
        }
    }

    @Override
    public ChatHistoryDto history(UUID matterId) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(pythonBaseUrl + "/chat/" + matterId))
                    .timeout(Duration.ofSeconds(10))
                    .GET()
                    .build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() >= 300) {
                throw new ChatService.AssistantUnavailableException("Assistant service returned " + response.statusCode());
            }
            return mapper.readValue(response.body(), ChatHistoryDto.class);
        } catch (IOException e) {
            throw new ChatService.AssistantUnavailableException("Assistant service unreachable", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ChatService.AssistantUnavailableException("Assistant call interrupted", e);
        }
    }
}
