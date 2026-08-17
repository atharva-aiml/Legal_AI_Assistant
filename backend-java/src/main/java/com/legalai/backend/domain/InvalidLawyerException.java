package com.legalai.backend.domain;

public class InvalidLawyerException extends RuntimeException {
    public InvalidLawyerException(String message) {
        super(message);
    }
}
