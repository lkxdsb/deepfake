package com.lingmou.deepfake.rag.retrieval;

import com.lingmou.deepfake.rag.keyword.KeywordHit;
import com.lingmou.deepfake.rag.model.RagChunk;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import com.lingmou.deepfake.rag.vector.VectorHit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class RrfFusion {
    public List<RetrievalCandidate> fuse(List<VectorHit> vectorHits, List<KeywordHit> keywordHits, int rrfK) {
        if (rrfK < 1) throw new IllegalArgumentException("rrfK must be positive");
        Map<String, MutableCandidate> candidates = new LinkedHashMap<>();
        for (VectorHit hit : vectorHits) {
            MutableCandidate candidate = candidates.computeIfAbsent(hit.chunk().chunkId(), ignored -> new MutableCandidate(hit.chunk()));
            candidate.vectorScore = hit.score();
            candidate.vectorRank = hit.rank();
        }
        for (KeywordHit hit : keywordHits) {
            MutableCandidate candidate = candidates.computeIfAbsent(hit.chunk().chunkId(), ignored -> new MutableCandidate(hit.chunk()));
            candidate.keywordScore = hit.score();
            candidate.keywordRank = hit.rank();
        }
        List<MutableCandidate> sorted = new ArrayList<>(candidates.values());
        sorted.forEach(candidate -> candidate.rrfScore = rrf(candidate.vectorRank, rrfK) + rrf(candidate.keywordRank, rrfK));
        sorted.sort(Comparator.comparingDouble((MutableCandidate candidate) -> candidate.rrfScore).reversed()
                .thenComparing(candidate -> candidate.chunk.chunkId()));
        List<RetrievalCandidate> result = new ArrayList<>();
        for (int index = 0; index < sorted.size(); index++) {
            MutableCandidate candidate = sorted.get(index);
            result.add(new RetrievalCandidate(candidate.chunk, candidate.vectorScore, candidate.vectorRank,
                    candidate.keywordScore, candidate.keywordRank, candidate.rrfScore, null, index + 1));
        }
        return List.copyOf(result);
    }

    private double rrf(Integer rank, int rrfK) {
        return rank == null ? 0.0 : 1.0 / (rrfK + rank);
    }

    private static final class MutableCandidate {
        private final RagChunk chunk;
        private Double vectorScore;
        private Integer vectorRank;
        private Double keywordScore;
        private Integer keywordRank;
        private double rrfScore;

        private MutableCandidate(RagChunk chunk) { this.chunk = chunk; }
    }
}
