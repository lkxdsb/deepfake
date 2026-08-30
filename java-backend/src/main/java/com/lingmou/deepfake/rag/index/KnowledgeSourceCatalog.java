package com.lingmou.deepfake.rag.index;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.config.RagPathResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class KnowledgeSourceCatalog {
    private final RagProperties properties;
    private final ObjectMapper objectMapper;
    private final RagPathResolver pathResolver;

    public KnowledgeSourceCatalog(RagProperties properties, ObjectMapper objectMapper, RagPathResolver pathResolver) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.pathResolver = pathResolver;
    }

    public List<KnowledgeSource> load() throws IOException {
        Path manifestPath = pathResolver.resolve(properties.getSourceManifest());
        if (!Files.isRegularFile(manifestPath)) throw new IOException("knowledge source manifest does not exist: " + manifestPath);
        KnowledgeSourceManifest manifest = objectMapper.readValue(manifestPath.toFile(), KnowledgeSourceManifest.class);
        Path root = pathResolver.resolve(properties.getKnowledgeBasePath());
        for (KnowledgeSource source : manifest.sources()) {
            Path resolved = root.resolve(source.path()).normalize();
            if (!resolved.startsWith(root) || !Files.isRegularFile(resolved)) {
                throw new IOException("knowledge source is outside root or missing: " + source.path());
            }
        }
        return manifest.sources();
    }
}
