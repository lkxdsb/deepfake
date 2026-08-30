package com.lingmou.deepfake.rag.index;

import java.time.Instant;

public record RagIndexBuildResult(
        boolean fullRebuild,
        Instant completedAt,
        int sourceCount,
        int addedOrChangedDocuments,
        int unchangedDocuments,
        int deletedDocuments,
        int indexedChunks) {
}
