package com.legalai.backend.application.chat;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatDtos.PinToggleDto;

import java.util.UUID;

/**
 * Port over the Java -> Python hand-off for chat (System Architecture SD-005).
 * Unlike {@code IngestionTrigger}, this call is synchronous — the browser is
 * waiting on an answer, not just an upload acknowledgement. Throws
 * {@link ChatService.NoReadyDocumentsException} / {@link ChatService.AssistantUnavailableException}
 * (and {@link ChatService.ChatMessageNotFoundException} for {@link #togglePin}).
 */
public interface ChatGateway {
    ChatMessageDto ask(UUID matterId, UUID lawyerId, String question);

    ChatHistoryDto history(UUID matterId);

    PinToggleDto togglePin(UUID matterId, UUID messageId, boolean pinned);
}
