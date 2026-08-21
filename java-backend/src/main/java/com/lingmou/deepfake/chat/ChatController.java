package com.lingmou.deepfake.chat;

import com.fasterxml.jackson.databind.node.ObjectNode;
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
    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/ask")
    public ApiResponse<ObjectNode> ask(@Valid @RequestBody ChatRequest request) {
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
            emitter.send(SseEmitter.event().name("start").data(Map.of("model", "configured")));
            ObjectNode result = chatService.ask(request);
            String answer = result.path("answer").asText();
            String model = result.path("model").asText();
            emitter.send(SseEmitter.event().name("delta").data(Map.of(
                    "type", "delta", "content", answer, "model", model)));
            emitter.send(SseEmitter.event().name("done").data(Map.of(
                    "type", "done", "answer", answer, "model", model)));
            emitter.complete();
        } catch (Exception exception) {
            try {
                emitter.send(SseEmitter.event().name("error").data(Map.of("message", exception.getMessage())));
                emitter.complete();
            } catch (IOException ioException) {
                emitter.completeWithError(ioException);
            }
        }
    }
}
