package com.legalai.backend.domain;

public class InvalidDeadlineException extends RuntimeException {
    public InvalidDeadlineException(String message) {
        super(message);
    }
}
