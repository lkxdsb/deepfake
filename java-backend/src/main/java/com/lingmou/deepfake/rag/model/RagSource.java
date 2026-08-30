package com.lingmou.deepfake.rag.model;

public record RagSource(
        String sourceId,
        String title,
        String path,
        String section,
        String chunkId,
        String quote,
        double score) {
}
