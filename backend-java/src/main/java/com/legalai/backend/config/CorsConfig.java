package com.legalai.backend.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * The frontend now calls this API cross-origin (different port) rather
 * than through same-origin Next.js API routes, so the browser enforces
 * CORS. Credentials must be enabled (not "*") for the session cookie to
 * be sent/accepted — System Architecture §5.
 */
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Value("${app.frontend-origin:http://localhost:3000}")
    private String frontendOrigin;

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(frontendOrigin)
                .allowedMethods("GET", "POST", "PATCH", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
