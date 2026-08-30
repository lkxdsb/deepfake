package com.lingmou.deepfake.rag.rerank;

import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import java.util.List;

public interface RerankerClient {
    List<RerankHit> rerank(String query, List<RetrievalCandidate> candidates);
}
