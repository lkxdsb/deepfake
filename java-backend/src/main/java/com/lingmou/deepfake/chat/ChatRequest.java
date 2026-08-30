package com.lingmou.deepfake.chat;

import com.lingmou.deepfake.rag.model.RetrievalMode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

public record ChatRequest(
        @NotBlank @Size(max = 2000) String question,
        @Size(max = 20) List<@Valid ChatMessage> history,
        RetrievalMode retrievalMode) {
    static final int MAX_HISTORY_MESSAGE_CHARS = 1800;

    public ChatRequest {
        history = history == null ? List.of() : history.stream()
                .filter(message -> message != null)
                .map(message -> new ChatMessage(message.role(), truncate(message.content())))
                .toList();
    }

    private static String truncate(String content) {
        if (content == null || content.length() <= MAX_HISTORY_MESSAGE_CHARS) return content;
        return content.substring(0, MAX_HISTORY_MESSAGE_CHARS - 1) + "…";
    }
}
