package com.lingmou.deepfake.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.model.RagSource;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import com.lingmou.deepfake.rag.model.RetrievalMode;
import com.lingmou.deepfake.rag.model.RetrievalResult;
import com.lingmou.deepfake.rag.retrieval.RagRetrievalService;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.logging.Logger;
import java.util.regex.Pattern;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.openai.api.OpenAiApi;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;

@Service
public class ChatService {
    private static final Logger LOGGER = Logger.getLogger(ChatService.class.getName());
    private static final String SYSTEM_PROMPT = """
            你是“灵眸鉴真”的 RAG 助手。只回答深度伪造检测、数字取证、合成内容识别、项目检测方法和灵眸鉴真平台使用方式。
            只能依据本轮给出的“知识库上下文”作答；知识库未覆盖的内容必须明确说明无法依据知识库回答，不能使用自身知识补全、猜测或编造。
            回答中的事实性结论必须使用对应的 [S1]、[S2] 引用。不得把文本问答描述为已经完成样本检测，不得编造论文、性能指标或平台能力，也不得提供违法用途的伪造制作指导。
            默认使用中文；如果用户要求检测具体样本，应提示其使用图片、视频或音频检测页面。
            """.strip();
    /**
     * Greetings are handled locally rather than sent to the model.  They are a UI
     * convenience, not a knowledge-base answer, so they must not pretend to have
     * sources or weaken the no-retrieval refusal rule for factual questions.
     */
    private static final Pattern GREETING = Pattern.compile("(?iu)^\\s*(?:hi|hello|hey|你好|您好|嗨|哈喽|在吗)[!！。,.，\\s]*$");
    private static final String GREETING_RESPONSE = "你好，我是灵眸鉴真的检测问答助手。你可以问我深度伪造检测原理、CASE / Bi-ST、音视频检测流程或平台使用方式。";
    private static final String GENERAL_PROMPT = """
            你是“灵眸鉴真”的 AI 助手。正常、自然地回答用户的问题，默认使用中文。
            当前问题没有检索到可引用的项目知识库资料，因此不要虚构 [S1] 等来源，也不要把一般性回答说成平台已实现的能力、项目论文结论或真实检测结果。
            对深度伪造检测、数字取证或平台相关的事实性问题，若缺少资料依据，应明确区分一般性说明与项目资料中的已验证信息。
            回答优先简洁清楚；除非用户明确要求展开，不要写成长篇教程或重复小结。
            """.strip();

    private final DeepfakeProperties.Chat chatProperties;
    private final RagProperties ragProperties;
    private final RagRetrievalService retrievalService;
    private final ObjectMapper objectMapper;
    private volatile ChatClient chatClient;

    public ChatService(DeepfakeProperties properties, RagProperties ragProperties, RagRetrievalService retrievalService,
            ObjectMapper objectMapper) {
        this.chatProperties = properties.getChat();
        this.ragProperties = ragProperties;
        this.retrievalService = retrievalService;
        this.objectMapper = objectMapper;
    }

    public RagChatResponse ask(ChatRequest request) {
        PreparedRagChat prepared = prepare(request);
        if (prepared.refused() || prepared.immediateResponse().answer() != null) return prepared.immediateResponse();
        String answer = usesNativeNvidiaClient() ? completeOpenAiCompletion(prepared)
                : chatClient().prompt().system(prepared.systemPrompt()).user(prepared.prompt()).call().content();
        if (answer == null || answer.isBlank()) throw new ApiException(HttpStatus.BAD_GATEWAY, "empty response from AI service");
        return new RagChatResponse(ensureCitation(answer, prepared.immediateResponse().sources()), chatProperties.getModel(),
                prepared.immediateResponse().retrievalMode(), prepared.immediateResponse().sources(), false);
    }

    public PreparedRagChat prepare(ChatRequest request) {
        RetrievalMode mode = request.retrievalMode() == null ? ragProperties.getDefaultRetrievalMode() : request.retrievalMode();
        if (GREETING.matcher(request.question()).matches()) {
            return new PreparedRagChat(new RagChatResponse(GREETING_RESPONSE, chatProperties.getModel(), mode, List.of(), false),
                    null, null, List.of(), false);
        }
        if (ragProperties.isEnabled()) {
            RetrievalResult result = retrieveSafely(request.question(), mode);
            if (result != null) {
                List<RetrievalCandidate> answerEvidence = answerEvidence(result.candidates());
                List<RagSource> sources = sources(answerEvidence);
                if (result.valid()) {
                    if (!ready()) throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI chat API key is not configured");
                    RagChatResponse response = new RagChatResponse(null, chatProperties.getModel(), result.mode(), sources, false);
                    return new PreparedRagChat(response, SYSTEM_PROMPT, userPrompt(request, sources, answerEvidence), sources, false);
                }
            }
        }
        if (!ready()) throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI chat API key is not configured");
        RagChatResponse response = new RagChatResponse(null, chatProperties.getModel(), mode, List.of(), false);
        return new PreparedRagChat(response, generalSystemPrompt(), generalPrompt(request), List.of(), false);
    }

    private RetrievalResult retrieveSafely(String question, RetrievalMode mode) {
        try {
            return retrievalService.retrieve(question, mode);
        } catch (RuntimeException exception) {
            LOGGER.warning("RAG retrieval is unavailable; using general chat without sources: " + exception.getMessage());
            return null;
        }
    }

    private boolean usesNativeNvidiaClient() {
        return chatProperties.getBaseUrl().contains("integrate.api.nvidia.com");
    }

    private String completeOpenAiCompletion(PreparedRagChat prepared) {
        try {
            String baseUrl = chatProperties.getBaseUrl().replaceAll("/+$", "");
            var payload = objectMapper.createObjectNode();
            payload.put("model", chatProperties.getModel());
            payload.put("temperature", chatProperties.getTemperature());
            payload.put("max_tokens", chatProperties.getMaxOutputTokens());
            var messages = payload.putArray("messages");
            messages.addObject().put("role", "system").put("content", prepared.systemPrompt());
            messages.addObject().put("role", "user").put("content", prepared.prompt());
            HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/chat/completions"))
                    .timeout(Duration.ofSeconds(chatProperties.getReadTimeoutSeconds()))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + chatProperties.getApiKey())
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(payload), StandardCharsets.UTF_8))
                    .build();
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(chatProperties.getConnectTimeoutSeconds())).build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new ApiException(HttpStatus.BAD_GATEWAY, "AI chat service returned HTTP " + response.statusCode());
            }
            JsonNode message = objectMapper.readTree(response.body()).path("choices").path(0).path("message");
            String content = message.path("content").asText("");
            return content.isBlank() ? message.path("reasoning_content").asText("") : content;
        } catch (ApiException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI chat request failed: " + exception.getMessage());
        }
    }

    public Flux<String> stream(PreparedRagChat prepared) {
        if (prepared.refused()) return Flux.empty();
        // Use the provider's OpenAI-compatible SSE endpoint directly. This avoids a Reactor TLS
        // handshake incompatibility observed with the hosted NVIDIA endpoint while retaining
        // Spring AI for the synchronous controlled-answer path.
        return Flux.create(sink -> CompletableFuture.runAsync(() -> streamOpenAiCompletion(prepared, sink))
                .exceptionally(exception -> { sink.error(exception); return null; }));
    }

    private void streamOpenAiCompletion(PreparedRagChat prepared, reactor.core.publisher.FluxSink<String> sink) {
        try {
            String baseUrl = chatProperties.getBaseUrl().replaceAll("/+$", "");
            var payload = objectMapper.createObjectNode();
            payload.put("model", chatProperties.getModel());
            payload.put("temperature", chatProperties.getTemperature());
            payload.put("max_tokens", chatProperties.getMaxOutputTokens());
            payload.put("stream", true);
            var messages = payload.putArray("messages");
            messages.addObject().put("role", "system").put("content", prepared.systemPrompt());
            messages.addObject().put("role", "user").put("content", prepared.prompt());
            HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(baseUrl + "/chat/completions"))
                    .timeout(Duration.ofSeconds(chatProperties.getReadTimeoutSeconds()))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(payload), StandardCharsets.UTF_8));
            request.header("Authorization", "Bearer " + chatProperties.getApiKey());
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(chatProperties.getConnectTimeoutSeconds())).build();
            HttpResponse<java.util.stream.Stream<String>> response = client.send(request.build(), HttpResponse.BodyHandlers.ofLines());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                try (var lines = response.body()) {
                    throw new ApiException(HttpStatus.BAD_GATEWAY, "AI streaming service returned HTTP " + response.statusCode());
                }
            }
            try (var lines = response.body()) {
                lines.filter(line -> line.startsWith("data:")).forEach(line -> emitSseDelta(line.substring(5).strip(), sink));
            }
            sink.complete();
        } catch (Exception exception) {
            throw new IllegalStateException("AI streaming request failed", exception);
        }
    }

    public String normalizeCitationBrackets(String answer) {
        return answer.replace('【', '[').replace('】', ']');
    }

    public String ensureCitation(String answer, List<RagSource> sources) {
        String normalized = normalizeCitationBrackets(answer).strip();
        if (!sources.isEmpty() && !normalized.matches("(?s).*\\[S\\d+]\\s*.*")) {
            normalized += "\n\n参考来源：[S1]";
        }
        return normalized;
    }

    private void emitSseDelta(String data, reactor.core.publisher.FluxSink<String> sink) {
        if ("[DONE]".equals(data) || data.isBlank() || sink.isCancelled()) return;
        try {
            JsonNode delta = objectMapper.readTree(data).path("choices").path(0).path("delta").path("content");
            if (!delta.isMissingNode() && !delta.isNull() && !delta.asText().isEmpty()) sink.next(delta.asText());
        } catch (Exception exception) {
            throw new IllegalStateException("invalid AI streaming event", exception);
        }
    }

    private ChatClient chatClient() {
        ChatClient existing = chatClient;
        if (existing != null) return existing;
        synchronized (this) {
            if (chatClient != null) return chatClient;
            OpenAiApi api = OpenAiApi.builder()
                    .baseUrl(chatProperties.getBaseUrl())
                    .completionsPath("/chat/completions")
                    .apiKey(chatProperties.getApiKey())
                    .build();
            OpenAiChatOptions options = OpenAiChatOptions.builder()
                    .model(chatProperties.getModel())
                    .temperature(chatProperties.getTemperature())
                    .build();
            chatClient = ChatClient.create(OpenAiChatModel.builder().openAiApi(api).defaultOptions(options).build());
            return chatClient;
        }
    }

    private boolean ready() {
        return chatProperties.getApiKey() != null && !chatProperties.getApiKey().isBlank();
    }

    private List<RagSource> sources(List<RetrievalCandidate> candidates) {
        List<RagSource> sources = new ArrayList<>();
        for (int index = 0; index < candidates.size(); index++) {
            RetrievalCandidate candidate = candidates.get(index);
            sources.add(new RagSource("S" + (index + 1), candidate.chunk().title(), candidate.chunk().path(),
                    candidate.chunk().section(), candidate.chunkId(), quote(candidate.chunk().content()), candidate.finalScore()));
        }
        return List.copyOf(sources);
    }

    /**
     * Keep a broader top-K inside retrieval for recall/evaluation, but do not overload the answer
     * model or UI with every weak candidate.  This is intentionally rank-based: vector, RRF and
     * reranker scores have different scales and should not share a hard-coded score threshold.
     */
    private List<RetrievalCandidate> answerEvidence(List<RetrievalCandidate> candidates) {
        int limit = Math.max(1, ragProperties.getAnswerSourceK());
        return candidates.stream().limit(limit).toList();
    }

    private String userPrompt(ChatRequest request, List<RagSource> sources, List<RetrievalCandidate> candidates) {
        StringBuilder prompt = new StringBuilder("知识库上下文：\n");
        for (int index = 0; index < candidates.size(); index++) {
            RetrievalCandidate candidate = candidates.get(index);
            prompt.append("[").append(sources.get(index).sourceId()).append("] ")
                    .append(candidate.chunk().title()).append(" | ").append(candidate.chunk().path())
                    .append(" | ").append(candidate.chunk().section()).append("\n")
                    .append(candidate.chunk().content()).append("\n\n");
        }
        if (!request.history().isEmpty()) {
            prompt.append("对话历史（仅用于理解上下文，不可作为事实来源）：\n");
            int start = Math.max(0, request.history().size() - Math.max(0, chatProperties.getMaxHistoryMessages()));
            for (ChatMessage message : request.history().subList(start, request.history().size())) {
                prompt.append(message.role()).append(": ").append(message.content().strip()).append("\n");
            }
        }
        return prompt.append("\n用户问题：").append(request.question().strip()).toString();
    }

    private String generalPrompt(ChatRequest request) {
        StringBuilder prompt = new StringBuilder();
        if (!request.history().isEmpty()) {
            prompt.append("对话历史：\n");
            int start = Math.max(0, request.history().size() - Math.max(0, chatProperties.getMaxHistoryMessages()));
            for (ChatMessage message : request.history().subList(start, request.history().size())) {
                prompt.append(message.role()).append(": ").append(message.content().strip()).append("\n");
            }
        }
        return prompt.append("\n用户问题：").append(request.question().strip()).toString();
    }

    private String generalSystemPrompt() {
        return GENERAL_PROMPT + "\n当前对话实际调用的模型标识为：" + chatProperties.getModel()
                + "。当用户询问你使用什么模型时，如实回答这个标识。";
    }

    private String quote(String content) {
        String normalized = content.replaceAll("\\s+", " ").strip();
        return normalized.length() <= 280 ? normalized : normalized.substring(0, 280) + "…";
    }
}
