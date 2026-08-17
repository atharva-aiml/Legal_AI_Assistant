package com.legalai.backend.web.dto;

import com.legalai.backend.application.activity.ActivityEntry;

import java.time.Instant;

public class ActivityDtos {
    public record ActivityEntryResponse(String type, String title, Instant timestamp) {
        public static ActivityEntryResponse from(ActivityEntry e) {
            return new ActivityEntryResponse(e.type(), e.title(), e.timestamp());
        }
    }
}
