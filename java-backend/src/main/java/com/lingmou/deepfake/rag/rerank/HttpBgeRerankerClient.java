package com.lingmou.deepfake.rag.rerank;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class HttpBgeRerankerClient implements RerankerClient {
    private final RagProperties.Reranker properties;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;

    public HttpBgeRerankerClient(RagProperties properties, ObjectMapper objectMapper) {
        this.properties = properties.getReranker();
        this.objectMapper = objectMapper;
        if (this.properties.getBaseUrl() == null || this.properties.getBaseUrl().isBlank()) {
            this.restClient = null;
            return;
        }
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(this.properties.getTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(this.properties.getTimeoutSeconds()));
        this.restClient = RestClient.builder().baseUrl(this.properties.getBaseUrl()).requestFactory(factory).build();
    }

    @Override
    public List<RerankHit> rerank(String query, List<RetrievalCandidate> candidates) {
        if (restClient == null) throw new RerankerUnavailableException("reranker service is not configured");
        int batchSize = properties.getMaxBatchCandidates();
        if (batchSize < 1) batchSize = candidates.size();
        List<RerankHit> hits = new ArrayList<>();
        for (int start = 0; start < candidates.size(); start += batchSize) {
            int end = Math.min(start + batchSize, candidates.size());
            hits.addAll(rerankBatch(query, candidates.subList(start, end), start));
        }
        return List.copyOf(hits);
    }

    private List<RerankHit> rerankBatch(String query, List<RetrievalCandidate> candidates, int offset) {
        ObjectNode payload = objectMapper.createObjectNode();
        payload.put("query", query);
        ArrayNode texts = payload.putArray("texts");
        candidates.forEach(candidate -> texts.add(candidate.chunk().content()));
        payload.put("raw_scores", false);
        try {
            JsonNode response = restClient.post().uri("/rerank").contentType(MediaType.APPLICATION_JSON)
                    .body(payload).retrieve().body(JsonNode.class);
            JsonNode results = response == null ? null : (response.isArray() ? response : response.path("results"));
            if (results == null || !results.isArray()) throw new RerankerUnavailableException("reranker returned an invalid response");
            return results.valueStream().map(item -> new RerankHit(offset + item.path("index").asInt(-1),
                    item.path("relevance_score").asDouble(item.path("score").asDouble(Double.NaN))))
                    .filter(hit -> hit.index() >= offset && !Double.isNaN(hit.score())).toList();
        } catch (RestClientException exception) {
            throw new RerankerUnavailableException("reranker service is unavailable", exception);
        }
    }
}
