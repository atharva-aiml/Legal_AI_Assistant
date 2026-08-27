package com.legalai.backend.application.chat;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatDtos.PinToggleDto;
import org.springframework.stereotype.Service;

import java.util.UUID;

/**
 * SD-005: thin by design — Java owns auth and Matter ownership (checked by
 * the controller before this is ever called, System Architecture SD-003's
 * "sole authority on session validity"), Python owns the entire chat domain
 * (retrieval, generation, grounding rules, persistence). This class exists
 * only so the controller depends on an application-layer service rather
 * than a port directly, matching every other entity in this codebase.
 */
@Service
public class ChatService {

    private final ChatGateway gateway;

    public ChatService(ChatGateway gateway) {
        this.gateway = gateway;
    }

    public ChatMessageDto ask(UUID matterId, UUID lawyerId, String question) {
        return gateway.ask(matterId, lawyerId, question);
    }

    public ChatHistoryDto history(UUID matterId) {
        return gateway.history(matterId);
    }

    public PinToggleDto togglePin(UUID matterId, UUID messageId, boolean pinned) {
        return gateway.togglePin(matterId, messageId, pinned);
    }

    /** ChatGPT-style edit-a-previous-message: creates a new sibling branch, never deletes/overwrites the original. */
    public ChatHistoryDto editMessage(UUID matterId, UUID messageId, UUID lawyerId, String question) {
        return gateway.editMessage(matterId, messageId, lawyerId, question);
    }

    /** Repoints which sibling branch is active — e.g. switching back to a pre-edit branch. Generates nothing new. */
    public ChatHistoryDto activateBranch(UUID matterId, UUID messageId) {
        return gateway.activateBranch(matterId, messageId);
    }

    /** 422: the Matter has no ready Document yet — nothing to ground an answer in. */
    public static class NoReadyDocumentsException extends RuntimeException {
    }

    /** 404: no message with that id in this Matter — I-34's pin toggle, and edit/activate-branch's message lookup. */
    public static class ChatMessageNotFoundException extends RuntimeException {
    }

    /** 400: the message being edited exists in this Matter but isn't a 'user' message — only a lawyer's own question can be edited. */
    public static class InvalidEditTargetException extends RuntimeException {
    }

    /** 502: the retrieval query or the LLM call itself failed in Python — a system fault, not a content gap. */
    public static class AssistantUnavailableException extends RuntimeException {
        public AssistantUnavailableException(String message) {
            super(message);
        }

        public AssistantUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
