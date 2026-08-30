package com.lingmou.deepfake.rag.vector;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.model.RagChunk;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ChromaVectorStoreTest {
    private final ObjectMapper objectMapper = new ObjectMapper();
    private HttpServer server;
    private final AtomicReference<JsonNode> upsertPayload = new AtomicReference<>();

    @BeforeEach
    void startServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/v2/tenants/default_tenant/databases/default_database/collections/lingmou-rag", this::collection);
        server.createContext("/api/v2/tenants/default_tenant/databases/default_database/collections/test-collection/upsert", this::upsert);
        server.createContext("/api/v2/tenants/default_tenant/databases/default_database/collections/test-collection/query", this::query);
        server.createContext("/api/v2/tenants/default_tenant/databases/default_database/collections/test-collection/delete", this::ok);
        server.start();
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    @Test
    void storesMetadataAndMapsChromaQueryResponseToRankedHits() {
        RagProperties properties = new RagProperties();
        properties.getChroma().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        EmbeddingClient embedding = inputs -> inputs.stream().map(value -> List.of(0.1, 0.2, 0.3)).toList();
        ChromaVectorStore store = new ChromaVectorStore(properties, embedding, objectMapper);
        RagChunk chunk = new RagChunk("chunk-1", "doc-1", "标题", "docs/guide.md", "方法", 3, "CASE 与 Bi-ST", "hash-1", Map.of());

        store.upsert(List.of(chunk));
        List<VectorHit> hits = store.search("视频检测", 5);
        store.deleteByDocumentId("doc-1");

        assertThat(upsertPayload.get().path("ids").get(0).asText()).isEqualTo("chunk-1");
        assertThat(upsertPayload.get().path("metadatas").get(0).path("section").asText()).isEqualTo("方法");
        assertThat(hits).singleElement().satisfies(hit -> {
            assertThat(hit.chunk().chunkId()).isEqualTo("chunk-1");
            assertThat(hit.rank()).isEqualTo(1);
            assertThat(hit.score()).isGreaterThan(0.0);
        });
    }

    private void collection(HttpExchange exchange) throws IOException {
        respond(exchange, 200, "{\"id\":\"test-collection\",\"name\":\"lingmou-rag\"}");
    }

    private void upsert(HttpExchange exchange) throws IOException {
        upsertPayload.set(objectMapper.readTree(exchange.getRequestBody()));
        respond(exchange, 200, "{}");
    }

    private void query(HttpExchange exchange) throws IOException {
        respond(exchange, 200, "{\"ids\":[[\"chunk-1\"]],\"documents\":[[\"CASE 与 Bi-ST\"]],\"metadatas\":[[{\"documentId\":\"doc-1\",\"title\":\"标题\",\"path\":\"docs/guide.md\",\"section\":\"方法\",\"chunkIndex\":3,\"contentHash\":\"hash-1\"}]],\"distances\":[[0.25]]}");
    }

    private void ok(HttpExchange exchange) throws IOException {
        respond(exchange, 200, "{}");
    }

    private void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }
}
