package com.lingmou.deepfake.chat;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.rag.model.RetrievalMode;
import java.util.List;
import org.junit.jupiter.api.Test;

class ChatRequestTest {
    @Test
    void truncatesOversizedHistoryMessagesBeforeValidationAndPromptAssembly() {
        ChatRequest request = new ChatRequest("继续解释", List.of(new ChatMessage("assistant", "a".repeat(3000))),
                RetrievalMode.HYBRID);

        assertThat(request.history()).singleElement().extracting(ChatMessage::content)
                .asString().hasSize(ChatRequest.MAX_HISTORY_MESSAGE_CHARS).endsWith("…");
    }
}
