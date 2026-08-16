package com.legalai.backend.domain;

public class InvalidTemplateException extends RuntimeException {
    public InvalidTemplateException(String message) {
        super(message);
    }
}
