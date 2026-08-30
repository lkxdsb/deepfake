package com.lingmou.deepfake.rag.vector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.rag.config.RagProperties;
import java.time.Duration;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class HttpEmbeddingClient implements EmbeddingClient {
    private final RagProperties.Embedding properties;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;

    public HttpEmbeddingClient(RagProperties properties, ObjectMapper objectMapper) {
        this.properties = properties.getEmbedding();
        this.objectMapper = objectMapper;
        if (properties.getEmbedding().getBaseUrl() == null || properties.getEmbedding().getBaseUrl().isBlank()) {
            this.restClient = null;
            return;
        }
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(5));
        factory.setReadTimeout(Duration.ofSeconds(30));
        this.restClient = RestClient.builder().baseUrl(properties.getEmbedding().getBaseUrl()).requestFactory(factory).build();
    }

    @Override
    public List<List<Double>> embed(List<String> inputs) {
        if (restClient == null) {
            throw new VectorStoreUnavailableException("embedding service is not configured");
        }
        ObjectNode payload = objectMapper.createObjectNode();
        payload.put("model", properties.getModel());
        ArrayNode input = payload.putArray("input");
        inputs.forEach(input::add);
        try {
            JsonNode response = restClient.post().uri("/embeddings")
                    .headers(headers -> addAuthorization(headers, properties.getApiKey()))
                    .contentType(MediaType.APPLICATION_JSON).body(payload).retrieve().body(JsonNode.class);
            if (response == null || !response.path("data").isArray() || response.path("data").size() != inputs.size()) {
                throw new VectorStoreUnavailableException("embedding service returned an invalid response");
            }
            return response.path("data").valueStream()
                    .map(item -> item.path("embedding").valueStream().map(JsonNode::asDouble).toList())
                    .toList();
        } catch (RestClientException exception) {
            throw new VectorStoreUnavailableException("embedding service is unavailable", exception);
        }
    }

    private void addAuthorization(HttpHeaders headers, String apiKey) {
        if (apiKey != null && !apiKey.isBlank()) {
            headers.setBearerAuth(apiKey);
        }
    }
}
