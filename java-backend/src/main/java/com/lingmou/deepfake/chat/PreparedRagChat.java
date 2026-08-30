package com.lingmou.deepfake.chat;

import com.lingmou.deepfake.rag.model.RagSource;
import java.util.List;

record PreparedRagChat(RagChatResponse immediateResponse, String systemPrompt, String prompt,
        List<RagSource> sources, boolean refused) { }
