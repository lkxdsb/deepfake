package com.lingmou.deepfake.rag.index;

import java.time.Instant;

public record RagIndexStatus(
        boolean initialized,
        Instant updatedAt,
        int sourceCount,
        int documentCount,
        int chunkCount,
        String indexPath) {
}
