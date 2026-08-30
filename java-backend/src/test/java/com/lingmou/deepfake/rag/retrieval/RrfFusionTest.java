package com.lingmou.deepfake.rag.retrieval;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import com.lingmou.deepfake.rag.keyword.KeywordHit;
import com.lingmou.deepfake.rag.model.RagChunk;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import com.lingmou.deepfake.rag.vector.VectorHit;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class RrfFusionTest {
    private final RrfFusion fusion = new RrfFusion();

    @Test
    void deduplicatesChunkAndCombinesBothRankContributions() {
        RagChunk shared = chunk("shared");
        RagChunk vectorOnly = chunk("vector-only");
        RagChunk keywordOnly = chunk("keyword-only");

        List<RetrievalCandidate> result = fusion.fuse(
                List.of(new VectorHit(vectorOnly, 0.9, 1, 0.1), new VectorHit(shared, 0.8, 2, 0.2)),
                List.of(new KeywordHit(shared, 4.0, 1), new KeywordHit(keywordOnly, 3.0, 2)), 60);

        assertThat(result).hasSize(3);
        RetrievalCandidate first = result.getFirst();
        assertThat(first.chunkId()).isEqualTo("shared");
        assertThat(first.vectorRank()).isEqualTo(2);
        assertThat(first.keywordRank()).isEqualTo(1);
        assertThat(first.rrfScore()).isCloseTo(1.0 / 62 + 1.0 / 61, within(0.000001));
        assertThat(result).extracting(RetrievalCandidate::finalRank).containsExactly(1, 2, 3);
    }

    private RagChunk chunk(String id) {
        return new RagChunk(id, "doc", "title", "docs/guide.md", "section", 0, "content", "hash", Map.of());
    }
}
