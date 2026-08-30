package com.lingmou.deepfake.rag.retrieval;

import com.lingmou.deepfake.rag.model.RetrievalMode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Request used by the retrieval-only evaluation endpoint. */
public record RagRetrievalRequest(
        @NotBlank @Size(max = 2000) String question,
        RetrievalMode retrievalMode) {
}
