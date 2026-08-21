package com.lingmou.deepfake.algorithm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.detection.MediaKind;
import java.nio.file.Path;
import java.time.Duration;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class HttpAlgorithmClient implements AlgorithmClient {
    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public HttpAlgorithmClient(DeepfakeProperties properties, ObjectMapper objectMapper) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(properties.getAlgorithmConnectTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(properties.getAlgorithmReadTimeoutSeconds()));
        this.restClient = RestClient.builder()
                .baseUrl(properties.getAlgorithmBaseUrl())
                .requestFactory(factory)
                .build();
        this.objectMapper = objectMapper;
    }

    @Override
    public ObjectNode detect(MediaKind kind, Path mediaPath, String taskId) {
        MultiValueMap<String, Object> multipart = new LinkedMultiValueMap<>();
        multipart.add("file", new FileSystemResource(mediaPath));
        multipart.add("task_id", taskId);
        try {
            JsonNode response = restClient.post()
                    .uri("/v1/inference/{kind}", kind.name().toLowerCase())
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(multipart)
                    .retrieve()
                    .body(JsonNode.class);
            return unwrap(response);
        } catch (RestClientException exception) {
            throw ApiExceptionFactory.algorithmUnavailable(exception);
        }
    }

    @Override
    public ObjectNode health() {
        try {
            JsonNode response = restClient.get().uri("/v1/health").retrieve().body(JsonNode.class);
            return asObject(response);
        } catch (RestClientException exception) {
            ObjectNode unavailable = objectMapper.createObjectNode();
            unavailable.put("status", "unavailable");
            unavailable.put("message", "algorithm service unavailable");
            return unavailable;
        }
    }

    private ObjectNode unwrap(JsonNode response) {
        if (response == null) {
            throw ApiExceptionFactory.invalidAlgorithmResponse("empty response");
        }
        JsonNode payload = response.has("data") && response.get("data").isObject()
                ? response.get("data")
                : response;
        return asObject(payload);
    }

    private ObjectNode asObject(JsonNode value) {
        if (value instanceof ObjectNode objectNode) {
            return objectNode.deepCopy();
        }
        throw ApiExceptionFactory.invalidAlgorithmResponse("expected a JSON object");
    }
}
