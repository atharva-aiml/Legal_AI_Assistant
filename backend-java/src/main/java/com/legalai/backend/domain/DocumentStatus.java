package com.legalai.backend.domain;

/** See MatterStatus for why these constants are deliberately lowercase (Postgres native enum). */
public enum DocumentStatus {
    uploading, processing, ready, failed
}
