package com.lingmou.deepfake.chat;

import com.lingmou.deepfake.rag.model.RagSource;
import com.lingmou.deepfake.rag.model.RetrievalMode;
import java.util.List;

public record RagChatResponse(
        String answer,
        String model,
        RetrievalMode retrievalMode,
        List<RagSource> sources,
        boolean refused) {
    public RagChatResponse {
        sources = sources == null ? List.of() : List.copyOf(sources);
    }
}
