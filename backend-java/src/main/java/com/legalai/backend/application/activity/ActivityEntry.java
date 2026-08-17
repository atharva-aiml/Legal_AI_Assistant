package com.legalai.backend.application.activity;

import java.time.Instant;

/**
 * I-32: not a new business rule — an aggregation of existing timestamped
 * facts (Document.createdAt, Deadline.updatedAt, a user Chat message's
 * createdAt) into one time-ordered view. {@code type} is a fixed
 * discriminator ("document" | "deadline" | "chat") the UI uses to pick an
 * icon; it carries no other meaning.
 */
public record ActivityEntry(String type, String title, Instant timestamp) {
}
