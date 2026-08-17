package com.legalai.backend.application.activity;

import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatService;
import com.legalai.backend.application.deadline.DeadlineService;
import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.Document;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

/**
 * I-32: a read-only merge across three sources this codebase already owns
 * separately — Java's own Document/Deadline repositories, and Python's
 * chat_messages via the same ChatGateway proxy the Chat panel's own history
 * call already uses (no new Python endpoint). Only a Chat *question*
 * (role='user') becomes an entry, not the assistant's answer — an
 * ask-and-answer round trip is one activity ("asked a question"), not two.
 */
@Service
public class ActivityService {

    private static final int MAX_TITLE_LENGTH = 80;

    private final DocumentService documentService;
    private final DeadlineService deadlineService;
    private final ChatService chatService;

    public ActivityService(DocumentService documentService, DeadlineService deadlineService, ChatService chatService) {
        this.documentService = documentService;
        this.deadlineService = deadlineService;
        this.chatService = chatService;
    }

    public List<ActivityEntry> forMatter(UUID firmId, UUID matterId) {
        List<ActivityEntry> entries = new ArrayList<>();

        for (Document d : documentService.list(firmId, matterId)) {
            entries.add(new ActivityEntry("document", "Document uploaded: " + d.fileName(), d.createdAt()));
        }

        for (Deadline dl : deadlineService.list(firmId, matterId)) {
            String label = dl.status() == DeadlineStatus.complete
                    ? "Deadline completed: " + dl.title()
                    : "Deadline added: " + dl.title();
            entries.add(new ActivityEntry("deadline", label, dl.updatedAt()));
        }

        // Best-effort: Python being unreachable shouldn't blank out the whole
        // timeline when Documents/Deadlines are perfectly able to render on
        // their own — same "don't lose what already succeeded" posture as
        // I-07's Recent Matters and I-28's chained deadline creation.
        try {
            for (ChatMessageDto m : chatService.history(matterId).messages()) {
                if (!"user".equals(m.role())) continue;
                entries.add(new ActivityEntry("chat", "Question asked: " + truncate(m.content()), m.createdAt()));
            }
        } catch (ChatService.AssistantUnavailableException ignored) {
            // Chat entries are simply omitted this time — not a reason to fail Documents/Deadlines.
        }

        entries.sort(Comparator.comparing(ActivityEntry::timestamp).reversed());
        return entries;
    }

    private static String truncate(String content) {
        String trimmed = content.trim();
        return trimmed.length() <= MAX_TITLE_LENGTH ? trimmed : trimmed.substring(0, MAX_TITLE_LENGTH - 1) + "…";
    }
}
