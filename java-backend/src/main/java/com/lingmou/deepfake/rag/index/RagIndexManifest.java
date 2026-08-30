package com.lingmou.deepfake.rag.index;

import java.time.Instant;
import java.util.Map;

public record RagIndexManifest(
        int version,
        Instant updatedAt,
        Map<String, DocumentManifestEntry> documents) {
    public RagIndexManifest {
        documents = documents == null ? Map.of() : Map.copyOf(documents);
    }

    public static RagIndexManifest empty() {
        return new RagIndexManifest(1, Instant.EPOCH, Map.of());
    }
}
