package com.legalai.backend.domain;

public class InvalidMatterException extends RuntimeException {
    public InvalidMatterException(String message) {
        super(message);
    }
}
