package com.lingmou.deepfake.chat;

import com.lingmou.deepfake.api.ApiResponse;
import jakarta.validation.Valid;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/chat")
public class ChatController {
    private static final int MAX_DELTA_CHARS = 80;
    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/ask")
    public ApiResponse<RagChatResponse> ask(@Valid @RequestBody ChatRequest request) {
        return ApiResponse.success(chatService.ask(request));
    }

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@Valid @RequestBody ChatRequest request) {
        SseEmitter emitter = new SseEmitter(120_000L);
        CompletableFuture.runAsync(() -> streamAnswer(request, emitter));
        return emitter;
    }

    private void streamAnswer(ChatRequest request, SseEmitter emitter) {
        try {
            PreparedRagChat prepared = chatService.prepare(request);
            RagChatResponse metadata = prepared.immediateResponse();
            emitter.send(SseEmitter.event().name("start").data(Map.of("model", metadata.model(),
                    "retrievalMode", metadata.retrievalMode().name(), "refused", metadata.refused())));
            if (prepared.refused()) {
                emitter.send(SseEmitter.event().name("sources").data(metadata.sources()));
                emitter.send(SseEmitter.event().name("done").data(Map.of("refused", true, "answer", metadata.answer(),
                        "model", metadata.model(), "retrievalMode", metadata.retrievalMode().name())));
                emitter.complete();
                return;
            }
            if (metadata.answer() != null) {
                sendDeltaChunks(emitter, metadata.answer(), metadata.model());
                emitter.send(SseEmitter.event().name("sources").data(metadata.sources()));
                emitter.send(SseEmitter.event().name("done").data(Map.of("refused", false, "answer", metadata.answer(),
                        "model", metadata.model(), "retrievalMode", metadata.retrievalMode().name())));
                emitter.complete();
                return;
            }
            StringBuilder answer = new StringBuilder();
            chatService.stream(prepared).doOnNext(delta -> {
                String normalizedDelta = chatService.normalizeCitationBrackets(delta);
                answer.append(normalizedDelta);
                sendDeltaChunks(emitter, normalizedDelta, metadata.model());
            }).doOnComplete(() -> {
                try {
                    String completedAnswer = chatService.ensureCitation(answer.toString(), metadata.sources());
                    if (completedAnswer.length() > answer.length()) {
                        String suffix = completedAnswer.substring(answer.length());
                        answer.append(suffix);
                        sendDeltaChunks(emitter, suffix, metadata.model());
                    }
                    emitter.send(SseEmitter.event().name("sources").data(metadata.sources()));
                    emitter.send(SseEmitter.event().name("done").data(Map.of("refused", false, "answer", answer.toString(),
                            "model", metadata.model(), "retrievalMode", metadata.retrievalMode().name())));
                    emitter.complete();
                } catch (IOException exception) {
                    emitter.completeWithError(exception);
                }
            }).doOnError(exception -> sendError(emitter, exception)).blockLast();
        } catch (Exception exception) {
            sendError(emitter, exception);
        }
    }

    private void sendDeltaChunks(SseEmitter emitter, String content, String model) {
        try {
            for (int start = 0; start < content.length(); start += MAX_DELTA_CHARS) {
                String delta = content.substring(start, Math.min(content.length(), start + MAX_DELTA_CHARS));
                emitter.send(SseEmitter.event().name("delta").data(Map.of("type", "delta", "content", delta, "model", model)));
            }
        } catch (IOException exception) {
            throw new IllegalStateException("unable to send stream delta", exception);
        }
    }

    private void sendError(SseEmitter emitter, Throwable exception) {
        try {
            emitter.send(SseEmitter.event().name("error").data(Map.of("message", exception.getMessage() == null ? "chat stream failed" : exception.getMessage())));
            emitter.complete();
        } catch (IOException ioException) {
            emitter.completeWithError(ioException);
        }
    }
}
