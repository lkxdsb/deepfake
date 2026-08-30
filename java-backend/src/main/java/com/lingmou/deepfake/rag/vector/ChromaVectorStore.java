package com.lingmou.deepfake.rag.vector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.model.RagChunk;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class ChromaVectorStore implements VectorStore {
    private final RagProperties.Chroma properties;
    private final EmbeddingClient embeddingClient;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;
    private volatile String collectionId;

    public ChromaVectorStore(RagProperties properties, EmbeddingClient embeddingClient, ObjectMapper objectMapper) {
        this.properties = properties.getChroma();
        this.embeddingClient = embeddingClient;
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(this.properties.getConnectTimeoutSeconds()));
        factory.setReadTimeout(Duration.ofSeconds(this.properties.getReadTimeoutSeconds()));
        this.restClient = RestClient.builder().baseUrl(this.properties.getBaseUrl()).requestFactory(factory).build();
    }

    @Override
    public void upsert(Collection<RagChunk> chunks) {
        if (chunks.isEmpty()) return;
        List<RagChunk> items = List.copyOf(chunks);
        List<List<Double>> embeddings = embeddingClient.embed(items.stream().map(RagChunk::content).toList());
        if (embeddings.size() != items.size()) {
            throw new VectorStoreUnavailableException("embedding service returned an unexpected vector count");
        }
        ObjectNode payload = objectMapper.createObjectNode();
        ArrayNode ids = payload.putArray("ids");
        ArrayNode documents = payload.putArray("documents");
        ArrayNode metadata = payload.putArray("metadatas");
        ArrayNode vectors = payload.putArray("embeddings");
        for (int index = 0; index < items.size(); index++) {
            RagChunk chunk = items.get(index);
            ids.add(chunk.chunkId());
            documents.add(chunk.content());
            metadata.add(metadata(chunk));
            ArrayNode vector = vectors.addArray();
            embeddings.get(index).forEach(vector::add);
        }
        post(collectionBasePath() + "/" + collectionId() + "/upsert", payload);
    }

    @Override
    public void deleteByDocumentId(String documentId) {
        ObjectNode payload = objectMapper.createObjectNode();
        payload.putObject("where").put("documentId", documentId);
        post(collectionBasePath() + "/" + collectionId() + "/delete", payload);
    }

    @Override
    public List<VectorHit> search(String question, int topK) {
        if (question == null || question.isBlank() || topK < 1) return List.of();
        List<List<Double>> vectors = embeddingClient.embed(List.of(question));
        if (vectors.size() != 1) throw new VectorStoreUnavailableException("embedding service returned no query vector");
        ObjectNode payload = objectMapper.createObjectNode();
        ArrayNode queryVectors = payload.putArray("query_embeddings");
        ArrayNode vector = queryVectors.addArray();
        vectors.getFirst().forEach(vector::add);
        payload.put("n_results", topK);
        payload.putArray("include").add("documents").add("metadatas").add("distances");
        JsonNode response = post(collectionBasePath() + "/" + collectionId() + "/query", payload);
        return parseHits(response);
    }

    private synchronized String collectionId() {
        if (collectionId != null) return collectionId;
        String endpoint = collectionBasePath() + "/" + properties.getCollection();
        try {
            JsonNode existing = get(endpoint);
            collectionId = existing.path("id").asText();
        } catch (VectorStoreUnavailableException exception) {
            if (!isNotFound(exception)) throw exception;
            ObjectNode create = objectMapper.createObjectNode();
            create.put("name", properties.getCollection());
            JsonNode created = post(collectionBasePath(), create);
            collectionId = created.path("id").asText();
        }
        if (collectionId == null || collectionId.isBlank()) {
            throw new VectorStoreUnavailableException("Chroma did not return a collection ID");
        }
        return collectionId;
    }

    private List<VectorHit> parseHits(JsonNode response) {
        JsonNode ids = firstRow(response.path("ids"));
        JsonNode documents = firstRow(response.path("documents"));
        JsonNode metadata = firstRow(response.path("metadatas"));
        JsonNode distances = firstRow(response.path("distances"));
        List<VectorHit> hits = new ArrayList<>();
        for (int index = 0; index < ids.size(); index++) {
            JsonNode fields = metadata.path(index);
            String content = documents.path(index).asText();
            double distance = distances.path(index).asDouble(Double.MAX_VALUE);
            RagChunk chunk = new RagChunk(ids.path(index).asText(), fields.path("documentId").asText(),
                    fields.path("title").asText(), fields.path("path").asText(), fields.path("section").asText(),
                    fields.path("chunkIndex").asInt(), content, fields.path("contentHash").asText(), metadata(fields));
            hits.add(new VectorHit(chunk, 1.0 / (1.0 + Math.max(0.0, distance)), index + 1, distance));
        }
        return List.copyOf(hits);
    }

    private JsonNode firstRow(JsonNode node) {
        return node.isArray() && !node.isEmpty() ? node.get(0) : objectMapper.createArrayNode();
    }

    private Map<String, String> metadata(JsonNode input) {
        Map<String, String> values = new LinkedHashMap<>();
        input.fields().forEachRemaining(item -> values.put(item.getKey(), item.getValue().asText()));
        return values;
    }

    private ObjectNode metadata(RagChunk chunk) {
        ObjectNode metadata = objectMapper.createObjectNode();
        metadata.put("documentId", chunk.documentId());
        metadata.put("title", chunk.title());
        metadata.put("path", chunk.path());
        metadata.put("section", chunk.section());
        metadata.put("chunkIndex", chunk.chunkIndex());
        metadata.put("contentHash", chunk.contentHash());
        return metadata;
    }

    private JsonNode get(String path) {
        try {
            return restClient.get().uri(path).headers(this::addAuthorization).retrieve().body(JsonNode.class);
        } catch (RestClientException exception) {
            throw wrap(exception);
        }
    }

    private JsonNode post(String path, ObjectNode payload) {
        try {
            return restClient.post().uri(path).headers(this::addAuthorization).contentType(MediaType.APPLICATION_JSON)
                    .body(payload).retrieve().body(JsonNode.class);
        } catch (RestClientException exception) {
            throw wrap(exception);
        }
    }

    private VectorStoreUnavailableException wrap(RestClientException exception) {
        String detail = exception.getMessage() == null ? "Chroma service is unavailable" : exception.getMessage();
        return new VectorStoreUnavailableException(detail, exception);
    }

    private boolean isNotFound(VectorStoreUnavailableException exception) {
        Throwable cause = exception.getCause();
        return cause instanceof RestClientResponseException response && response.getStatusCode().value() == 404;
    }

    private void addAuthorization(HttpHeaders headers) {
        if (properties.getAuthToken() != null && !properties.getAuthToken().isBlank()) {
            headers.set("x-chroma-token", properties.getAuthToken());
        }
    }

    private String collectionBasePath() {
        return "/api/v2/tenants/" + properties.getTenant() + "/databases/" + properties.getDatabase() + "/collections";
    }
}
