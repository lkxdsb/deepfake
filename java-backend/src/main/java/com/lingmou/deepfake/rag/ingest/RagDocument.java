package com.lingmou.deepfake.rag.ingest;

import java.nio.file.Path;

public record RagDocument(
        String documentId,
        Path source,
        String relativePath,
        String title,
        String content,
        String contentHash) {
}
