package com.lingmou.deepfake.rag.retrieval;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.config.RagPathResolver;
import com.lingmou.deepfake.rag.keyword.KeywordHit;
import com.lingmou.deepfake.rag.keyword.KeywordRetriever;
import com.lingmou.deepfake.rag.model.RagChunk;
import com.lingmou.deepfake.rag.model.RetrievalMode;
import com.lingmou.deepfake.rag.model.RetrievalResult;
import com.lingmou.deepfake.rag.rerank.RerankHit;
import com.lingmou.deepfake.rag.rerank.RerankerClient;
import com.lingmou.deepfake.rag.rerank.RerankerUnavailableException;
import com.lingmou.deepfake.rag.vector.VectorHit;
import com.lingmou.deepfake.rag.vector.VectorStore;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class RagRetrievalServiceTest {
    @Test
    void reranksHybridCandidatesAndMarksValidResult() {
        RagChunk first = chunk("first");
        RagChunk second = chunk("second");
        VectorStore vector = new FakeVectorStore(List.of(new VectorHit(first, 0.9, 1, 0.1), new VectorHit(second, 0.8, 2, 0.2)));
        KeywordRetriever keyword = (path, query, topK) -> List.of(new KeywordHit(first, 4.0, 1), new KeywordHit(second, 3.0, 2));
        RerankerClient reranker = (query, candidates) -> List.of(new RerankHit(0, 0.2), new RerankHit(1, 0.9));
        RagProperties properties = properties(true, 0.1);

        RetrievalResult result = new RagRetrievalService(properties, vector, keyword, new RrfFusion(), reranker, new RagPathResolver())
                .retrieve("检测方法", RetrievalMode.HYBRID_RERANK);

        assertThat(result.valid()).isTrue();
        assertThat(result.mode()).isEqualTo(RetrievalMode.HYBRID_RERANK);
        assertThat(result.candidates()).extracting(candidate -> candidate.chunkId()).containsExactly("second", "first");
        assertThat(result.candidates().getFirst().rerankScore()).isEqualTo(0.9);
    }

    @Test
    void fallsBackToHybridWhenRerankerFails() {
        RagChunk first = chunk("first");
        VectorStore vector = new FakeVectorStore(List.of(new VectorHit(first, 0.9, 1, 0.1)));
        KeywordRetriever keyword = (path, query, topK) -> List.of(new KeywordHit(first, 4.0, 1));
        RerankerClient unavailable = (query, candidates) -> { throw new RerankerUnavailableException("offline"); };

        RetrievalResult result = new RagRetrievalService(properties(true, 0.01), vector, keyword, new RrfFusion(), unavailable, new RagPathResolver())
                .retrieve("检测方法", RetrievalMode.HYBRID_RERANK);

        assertThat(result.valid()).isTrue();
        assertThat(result.mode()).isEqualTo(RetrievalMode.HYBRID);
        assertThat(result.candidates()).singleElement().satisfies(candidate -> assertThat(candidate.rerankScore()).isNull());
    }

    @Test
    void refusesWhenNoResultPassesThreshold() {
        VectorStore vector = new FakeVectorStore(List.of());
        KeywordRetriever keyword = (path, query, topK) -> List.of();
        RerankerClient reranker = (query, candidates) -> List.of();

        RetrievalResult result = new RagRetrievalService(properties(false, 0.01), vector, keyword, new RrfFusion(), reranker, new RagPathResolver())
                .retrieve("无关问题", RetrievalMode.HYBRID);

        assertThat(result.valid()).isFalse();
        assertThat(result.rejectionReason()).contains("threshold");
    }

    @Test
    void rejectsWeakSemanticVectorMatchEvenWhenRrfHasCandidates() {
        RagChunk weak = chunk("weak");
        VectorStore vector = new FakeVectorStore(List.of(new VectorHit(weak, 0.30, 1, 2.3)));
        KeywordRetriever keyword = (path, query, topK) -> List.of(new KeywordHit(weak, 8.0, 1));

        RetrievalResult result = new RagRetrievalService(properties(false, 0.01), vector, keyword,
                new RrfFusion(), (query, candidates) -> List.of(), new RagPathResolver())
                .retrieve("隐含语境问题", RetrievalMode.HYBRID);

        assertThat(result.valid()).isFalse();
        assertThat(result.rejectionReason()).contains("relevance");
    }

    @Test
    void diversifiesTopResultsAcrossDocuments() {
        RagChunk first = chunk("first", "doc-a");
        RagChunk second = chunk("second", "doc-a");
        RagChunk third = chunk("third", "doc-b");
        RagChunk fourth = chunk("fourth", "doc-c");
        VectorStore vector = new FakeVectorStore(List.of(
                new VectorHit(first, 0.99, 1, 0.0), new VectorHit(second, 0.98, 2, 0.0),
                new VectorHit(third, 0.97, 3, 0.0), new VectorHit(fourth, 0.96, 4, 0.0)));
        RagProperties properties = properties(false, 0.1);
        properties.setTopK(3);
        properties.setMaxChunksPerDocument(1);

        RetrievalResult result = new RagRetrievalService(properties, vector, (path, query, topK) -> List.of(),
                new RrfFusion(), (query, candidates) -> List.of(), new RagPathResolver())
                .retrieve("检测方法", RetrievalMode.VECTOR);

        assertThat(result.candidates()).extracting(candidate -> candidate.chunkId()).containsExactly("first", "third", "fourth");
        assertThat(result.candidates()).extracting(candidate -> candidate.finalRank()).containsExactly(1, 2, 3);
    }

    private RagProperties properties(boolean rerankerEnabled, double threshold) {
        RagProperties properties = new RagProperties();
        properties.setIndexPath(Path.of("target/test-rag-index"));
        properties.setTopK(5);
        properties.setRerankCandidateK(10);
        properties.setRefusalThreshold(threshold);
        properties.getReranker().setEnabled(rerankerEnabled);
        return properties;
    }

    private RagChunk chunk(String id) {
        return chunk(id, "doc-" + id);
    }

    private RagChunk chunk(String id, String documentId) {
        return new RagChunk(id, documentId, "title", "docs/guide.md", "section", 0, "content " + id, "hash", Map.of());
    }

    private static final class FakeVectorStore implements VectorStore {
        private final List<VectorHit> hits;
        private FakeVectorStore(List<VectorHit> hits) { this.hits = hits; }
        @Override public void upsert(java.util.Collection<RagChunk> chunks) { }
        @Override public void deleteByDocumentId(String documentId) { }
        @Override public List<VectorHit> search(String question, int topK) { return hits; }
    }
}
