package com.legalai.backend.application.chat;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatDtos.PinToggleDto;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ChatServiceTest {

    static class InMemoryChatGateway implements ChatGateway {
        ChatMessageDto askResponse;
        ChatHistoryDto historyResponse = new ChatHistoryDto(List.of());
        PinToggleDto togglePinResponse;
        ChatHistoryDto editMessageResponse;
        ChatHistoryDto activateBranchResponse;
        RuntimeException askException;
        RuntimeException togglePinException;
        RuntimeException editMessageException;
        RuntimeException activateBranchException;
        UUID lastMatterId;
        UUID lastLawyerId;
        String lastQuestion;
        UUID lastMessageId;
        Boolean lastPinned;

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

        @Override
        public PinToggleDto togglePin(UUID matterId, UUID messageId, boolean pinned) {
            lastMatterId = matterId;
            lastMessageId = messageId;
            lastPinned = pinned;
            if (togglePinException != null) throw togglePinException;
            return togglePinResponse;
        }

        @Override
        public ChatHistoryDto editMessage(UUID matterId, UUID messageId, UUID lawyerId, String question) {
            lastMatterId = matterId;
            lastMessageId = messageId;
            lastLawyerId = lawyerId;
            lastQuestion = question;
            if (editMessageException != null) throw editMessageException;
            return editMessageResponse;
        }

        @Override
        public ChatHistoryDto activateBranch(UUID matterId, UUID messageId) {
            lastMatterId = matterId;
            lastMessageId = messageId;
            if (activateBranchException != null) throw activateBranchException;
            return activateBranchResponse;
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
        gateway.askResponse = new ChatMessageDto(UUID.randomUUID(), matterId, null, "assistant", "Rs. 85,000 [1].", null, List.of(), false, true, false, null, List.of());

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
        ChatMessageDto message = new ChatMessageDto(UUID.randomUUID(), matterId, lawyerId, "user", "What is the rent?", null, List.of(), null, null, false, null, List.of());
        gateway.historyResponse = new ChatHistoryDto(List.of(message));

        ChatHistoryDto result = service.history(matterId);

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(1, result.messages().size());
    }

    @Test
    void togglePinForwardsTheMessageIdAndPinnedFlagAndReturnsTheGatewaysResult() {
        UUID messageId = UUID.randomUUID();
        gateway.togglePinResponse = new PinToggleDto(messageId, true);

        PinToggleDto result = service.togglePin(matterId, messageId, true);

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(messageId, gateway.lastMessageId);
        assertEquals(true, gateway.lastPinned);
        assertTrue(result.pinned());
    }

    @Test
    void togglePinPropagatesChatMessageNotFoundExceptionForTheControllerTo404() {
        gateway.togglePinException = new ChatService.ChatMessageNotFoundException();
        assertThrows(ChatService.ChatMessageNotFoundException.class, () -> service.togglePin(matterId, UUID.randomUUID(), true));
    }

    @Test
    void editMessageForwardsTheMessageIdLawyerIdAndQuestionAndReturnsTheGatewaysFullActivePath() {
        UUID messageId = UUID.randomUUID();
        ChatMessageDto editedMessage = new ChatMessageDto(messageId, matterId, lawyerId, "user", "What is the updated rent?", null, List.of(), null, null, false, null, List.of(messageId.toString()));
        gateway.editMessageResponse = new ChatHistoryDto(List.of(editedMessage));

        ChatHistoryDto result = service.editMessage(matterId, messageId, lawyerId, "What is the updated rent?");

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(messageId, gateway.lastMessageId);
        assertEquals(lawyerId, gateway.lastLawyerId);
        assertEquals("What is the updated rent?", gateway.lastQuestion);
        assertEquals(1, result.messages().size());
    }

    @Test
    void editMessagePropagatesChatMessageNotFoundExceptionForTheControllerTo404() {
        gateway.editMessageException = new ChatService.ChatMessageNotFoundException();
        assertThrows(ChatService.ChatMessageNotFoundException.class, () -> service.editMessage(matterId, UUID.randomUUID(), lawyerId, "anything"));
    }

    @Test
    void editMessagePropagatesInvalidEditTargetExceptionForTheControllerTo400() {
        gateway.editMessageException = new ChatService.InvalidEditTargetException();
        assertThrows(ChatService.InvalidEditTargetException.class, () -> service.editMessage(matterId, UUID.randomUUID(), lawyerId, "anything"));
    }

    @Test
    void editMessagePropagatesAssistantUnavailableExceptionForTheControllerTo502() {
        gateway.editMessageException = new ChatService.AssistantUnavailableException("down");
        assertThrows(ChatService.AssistantUnavailableException.class, () -> service.editMessage(matterId, UUID.randomUUID(), lawyerId, "anything"));
    }

    @Test
    void activateBranchForwardsTheMessageIdAndReturnsTheGatewaysFullActivePath() {
        UUID messageId = UUID.randomUUID();
        ChatMessageDto reactivatedMessage = new ChatMessageDto(messageId, matterId, lawyerId, "user", "What is the rent?", null, List.of(), null, null, false, null, List.of(messageId.toString()));
        gateway.activateBranchResponse = new ChatHistoryDto(List.of(reactivatedMessage));

        ChatHistoryDto result = service.activateBranch(matterId, messageId);

        assertEquals(matterId, gateway.lastMatterId);
        assertEquals(messageId, gateway.lastMessageId);
        assertEquals(1, result.messages().size());
    }

    @Test
    void activateBranchPropagatesChatMessageNotFoundExceptionForTheControllerTo404() {
        gateway.activateBranchException = new ChatService.ChatMessageNotFoundException();
        assertThrows(ChatService.ChatMessageNotFoundException.class, () -> service.activateBranch(matterId, UUID.randomUUID()));
    }
}
