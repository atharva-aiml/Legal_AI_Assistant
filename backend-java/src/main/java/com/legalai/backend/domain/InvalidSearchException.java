package com.legalai.backend.domain;

public class InvalidSearchException extends RuntimeException {
    public InvalidSearchException(String message) {
        super(message);
    }
}
