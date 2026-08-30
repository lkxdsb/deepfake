package com.lingmou.deepfake.rag.retrieval;

import com.lingmou.deepfake.rag.model.RetrievalMode;
import java.util.List;

/** A model-free retrieval trace. Scores and ranks are retained for audit. */
public record RagRetrievalResponse(
        RetrievalMode retrievalMode,
        boolean valid,
        String rejectionReason,
        List<RagRetrievalHit> hits) {
    public RagRetrievalResponse {
        hits = hits == null ? List.of() : List.copyOf(hits);
    }
}
