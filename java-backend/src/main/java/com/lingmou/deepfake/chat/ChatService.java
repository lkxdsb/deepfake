package com.lingmou.deepfake.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import java.time.Duration;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Service
public class ChatService {
    private static final String SYSTEM_PROMPT = """
            你是“灵眸鉴真”的 AI 助手，只回答深度伪造检测、数字取证、AI 合成内容识别和本平台使用相关问题。
            不得把文本问答描述为已经完成样本检测，不得编造论文、性能指标或平台能力，也不得提供违法用途的伪造制作指导。
            默认使用中文；如果用户要求检测具体样本，应提示其使用图片、视频或音频检测页面。
            """.strip();

    private final DeepfakeProperties.Chat properties;
    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public ChatService(DeepfakeProperties properties, ObjectMapper objectMapper) {
        this.properties = properties.getChat();
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(this.properties.getConnectTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(this.properties.getReadTimeoutSeconds()));
        this.restClient = RestClient.builder()
                .baseUrl(this.properties.getBaseUrl())
                .requestFactory(factory)
                .build();
    }

    public boolean ready() {
        return properties.getApiKey() != null && !properties.getApiKey().isBlank();
    }

    public ObjectNode ask(ChatRequest request) {
        if (!ready()) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI chat API key is not configured");
        }

        ObjectNode payload = objectMapper.createObjectNode();
        payload.put("model", properties.getModel());
        payload.put("temperature", properties.getTemperature());
        payload.put("stream", false);
        payload.set("messages", messages(request));

        try {
            JsonNode response = restClient.post()
                    .uri("/chat/completions")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getApiKey())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(payload)
                    .retrieve()
                    .body(JsonNode.class);
            String answer = response == null ? "" : response.path("choices").path(0).path("message").path("content").asText();
            if (answer.isBlank()) {
                throw new ApiException(HttpStatus.BAD_GATEWAY, "empty response from AI service");
            }
            ObjectNode result = objectMapper.createObjectNode();
            result.put("answer", answer);
            result.put("model", response.path("model").asText(properties.getModel()));
            return result;
        } catch (RestClientException exception) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI service unavailable");
        }
    }

    private ArrayNode messages(ChatRequest request) {
        ArrayNode messages = objectMapper.createArrayNode();
        addMessage(messages, "system", SYSTEM_PROMPT);
        List<ChatMessage> history = request.history();
        int start = Math.max(0, history.size() - Math.max(0, properties.getMaxHistoryMessages()));
        for (ChatMessage message : history.subList(start, history.size())) {
            addMessage(messages, message.role(), message.content());
        }
        addMessage(messages, "user", request.question());
        return messages;
    }

    private void addMessage(ArrayNode messages, String role, String content) {
        ObjectNode message = messages.addObject();
        message.put("role", role);
        message.put("content", content.strip());
    }
}
