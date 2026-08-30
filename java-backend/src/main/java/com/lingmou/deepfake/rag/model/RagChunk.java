package com.lingmou.deepfake.rag.model;

import java.util.Map;

public record RagChunk(
        String chunkId,
        String documentId,
        String title,
        String path,
        String section,
        int chunkIndex,
        String content,
        String contentHash,
        Map<String, String> metadata) {
    public RagChunk {
        metadata = metadata == null ? Map.of() : Map.copyOf(metadata);
    }
}
