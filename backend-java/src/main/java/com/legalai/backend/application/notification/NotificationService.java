package com.legalai.backend.application.notification;

import com.legalai.backend.domain.Notification;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class NotificationService {

    private final NotificationRepository repository;

    public NotificationService(NotificationRepository repository) {
        this.repository = repository;
    }

    public List<Notification> list(UUID lawyerId) {
        return repository.listByLawyer(lawyerId);
    }

    public Optional<Notification> markRead(UUID lawyerId, UUID id) {
        return repository.markRead(lawyerId, id);
    }

    public int markAllRead(UUID lawyerId) {
        return repository.markAllRead(lawyerId);
    }
}
