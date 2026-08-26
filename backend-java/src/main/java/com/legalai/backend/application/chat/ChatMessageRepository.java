package com.legalai.backend.application.chat;

import java.util.UUID;

/**
 * Cascade-delete-only port. SD-005: Python owns the chat domain's reads/
 * writes (ChatService talks to it exclusively through ChatGateway/
 * HttpChatGateway, never touching chat_messages directly) — but
 * chat_messages lives in the one shared Postgres database both backends
 * point at (System Architecture §3, /database is the single source of
 * truth regardless of which backend reads it), and Client/Matter
 * cascade-delete (ClientService.deleteCascade) needs a direct path to wipe
 * a Matter's chat history at the DB level rather than round-tripping
 * through Python for a low-level cleanup step. Citations cascade
 * automatically when a chat message is deleted
 * (citations.chat_message_id ON DELETE CASCADE) — never touched directly
 * here.
 */
public interface ChatMessageRepository {
    void deleteByMatter(UUID matterId);
}
