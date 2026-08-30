package com.lingmou.deepfake.rag.index;

import java.util.List;

public record DocumentManifestEntry(
        String documentId,
        String path,
        String contentHash,
        List<String> chunkIds) {
    public DocumentManifestEntry {
        chunkIds = chunkIds == null ? List.of() : List.copyOf(chunkIds);
    }
}
