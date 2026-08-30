package com.lingmou.deepfake.rag.config;

import java.nio.file.Path;
import org.springframework.stereotype.Component;

/** Resolves relative RAG paths against the process directory captured before Tomcat mutates its doc base. */
@Component
public class RagPathResolver {
    private final Path applicationRoot;

    public RagPathResolver() {
        this.applicationRoot = Path.of(System.getProperty("deepfake.application-root", System.getProperty("user.dir")))
                .toAbsolutePath().normalize();
    }

    public Path resolve(Path configuredPath) {
        return configuredPath.isAbsolute() ? configuredPath.normalize() : applicationRoot.resolve(configuredPath).normalize();
    }
}
