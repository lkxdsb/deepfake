package com.lingmou.deepfake.rag.model;

import java.util.List;

public record RetrievalResult(
        RetrievalMode mode,
        List<RetrievalCandidate> candidates,
        boolean valid,
        String rejectionReason) {
    public RetrievalResult {
        candidates = candidates == null ? List.of() : List.copyOf(candidates);
    }
}
