package com.legalai.backend.application.chat;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ChatServiceTest {

    static class InMemoryChatGateway implements ChatGateway {
        ChatMessageDto askResponse;
        ChatHistoryDto historyResponse = new ChatHistoryDto(List.of());
        RuntimeException askException;
        UUID lastMatterId;
        UUID lastLawyerId;
        String lastQuestion;

        @Override
        public ChatMessageDto ask(UUID matterId, UUID lawyerId, String question) {
            lastMatterId = matterId;
            lastLawyerId = lawyerId;
            lastQuestion = question;
            if (askException != null) throw askException;
            return askResponse;
        }

        @Override
        public ChatHistoryDto history(UUID matterId) {
            lastMatterId = matterId;
            return historyResponse;
        }
    }

    private InMemoryChatGateway gateway;
    private ChatService service;
    private final UUID matterId = UUID.randomUUID();
    private final UUID lawyerId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        gateway = new InMemoryChatGateway();
        service = new ChatService(gateway);
    }

    @Test
    void askForwardsTheQuestionAndReturnsTheGatewaysAnswer() {
        gateway.askResponse = new ChatMessageDto(UUID.randomUUID(), matterId, null, "assistant", "Rs. 85,000 [1].", null, List.of(), false);

        ChatMessageDto result = service.ask(matterId, lawyerId, "What is the rent?");

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(lawyerId, gateway.lastLawyerId);
        assertEquals("What is the rent?", gateway.lastQuestion);
        assertEquals("Rs. 85,000 [1].", result.content());
    }

    @Test
    void askPropagatesNoReadyDocumentsExceptionForTheControllerTo422() {
        gateway.askException = new ChatService.NoReadyDocumentsException();
        assertThrows(ChatService.NoReadyDocumentsException.class, () -> service.ask(matterId, lawyerId, "anything"));
    }

    @Test
    void askPropagatesAssistantUnavailableExceptionForTheControllerTo502() {
        gateway.askException = new ChatService.AssistantUnavailableException("down");
        assertThrows(ChatService.AssistantUnavailableException.class, () -> service.ask(matterId, lawyerId, "anything"));
    }

    @Test
    void historyForwardsTheMatterIdAndReturnsTheGatewaysMessages() {
        ChatMessageDto message = new ChatMessageDto(UUID.randomUUID(), matterId, lawyerId, "user", "What is the rent?", null, List.of(), null);
        gateway.historyResponse = new ChatHistoryDto(List.of(message));

        ChatHistoryDto result = service.history(matterId);

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(1, result.messages().size());
    }
}
