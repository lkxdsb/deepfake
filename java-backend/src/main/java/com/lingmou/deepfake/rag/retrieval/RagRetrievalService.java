package com.lingmou.deepfake.rag.retrieval;

import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.config.RagPathResolver;
import com.lingmou.deepfake.rag.keyword.KeywordHit;
import com.lingmou.deepfake.rag.keyword.KeywordRetriever;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import com.lingmou.deepfake.rag.model.RetrievalMode;
import com.lingmou.deepfake.rag.model.RetrievalResult;
import com.lingmou.deepfake.rag.rerank.RerankHit;
import com.lingmou.deepfake.rag.rerank.RerankerClient;
import com.lingmou.deepfake.rag.rerank.RerankerUnavailableException;
import com.lingmou.deepfake.rag.vector.VectorHit;
import com.lingmou.deepfake.rag.vector.VectorStore;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.logging.Logger;
import org.springframework.stereotype.Service;

@Service
public class RagRetrievalService {
    private static final Logger LOGGER = Logger.getLogger(RagRetrievalService.class.getName());
    private final RagProperties properties;
    private final VectorStore vectorStore;
    private final KeywordRetriever keywordRetriever;
    private final RrfFusion rrfFusion;
    private final RerankerClient rerankerClient;
    private final RagPathResolver pathResolver;

    public RagRetrievalService(RagProperties properties, VectorStore vectorStore, KeywordRetriever keywordRetriever,
                               RrfFusion rrfFusion, RerankerClient rerankerClient, RagPathResolver pathResolver) {
        this.properties = properties;
        this.vectorStore = vectorStore;
        this.keywordRetriever = keywordRetriever;
        this.rrfFusion = rrfFusion;
        this.rerankerClient = rerankerClient;
        this.pathResolver = pathResolver;
    }

    public RetrievalResult retrieve(String question, RetrievalMode mode) {
        int recallK = mode == RetrievalMode.HYBRID_RERANK ? properties.getRerankCandidateK() : properties.getTopK();
        List<VectorHit> vectorHits = mode == RetrievalMode.VECTOR ? vectorStore.search(question, properties.getTopK())
                : vectorStore.search(question, recallK);
        List<RetrievalCandidate> candidates;
        if (mode == RetrievalMode.VECTOR) {
            candidates = vectorCandidates(vectorHits);
        } else {
            List<KeywordHit> keywordHits = keywordHits(question, recallK);
            candidates = rrfFusion.fuse(vectorHits, keywordHits, properties.getRrfK());
        }
        RetrievalMode effectiveMode = mode;
        if (mode == RetrievalMode.HYBRID_RERANK) {
            RerankResult rerankResult = properties.getReranker().isEnabled()
                    ? rerankOrFallback(question, candidates)
                    : new RerankResult(candidates, false);
            candidates = rerankResult.candidates();
            if (!rerankResult.applied()) effectiveMode = RetrievalMode.HYBRID;
        }
        List<RetrievalCandidate> topCandidates = diversify(candidates);
        boolean hasStrongSemanticMatch = topCandidates.stream()
                .map(RetrievalCandidate::vectorScore)
                .filter(java.util.Objects::nonNull)
                .anyMatch(score -> score >= properties.getMinVectorScore());
        boolean valid = !topCandidates.isEmpty() && topCandidates.getFirst().finalScore() >= properties.getRefusalThreshold()
                && hasStrongSemanticMatch;
        String rejectionReason = valid ? null : "no retrieval result passed the configured relevance thresholds";
        return new RetrievalResult(effectiveMode, topCandidates, valid, rejectionReason);
    }

    private List<KeywordHit> keywordHits(String question, int topK) {
        try {
            return keywordRetriever.search(pathResolver.resolve(properties.getIndexPath()).resolve("lucene"), question, topK);
        } catch (IOException exception) {
            throw new IllegalStateException("Lucene index is unavailable", exception);
        }
    }

    private List<RetrievalCandidate> vectorCandidates(List<VectorHit> hits) {
        List<RetrievalCandidate> candidates = new ArrayList<>();
        for (VectorHit hit : hits) {
            candidates.add(new RetrievalCandidate(hit.chunk(), hit.score(), hit.rank(), null, null, null, null, hit.rank()));
        }
        return List.copyOf(candidates);
    }

    /**
     * A long document can occupy every top-K slot with adjacent chunks. Keep the best-ranked
     * candidates while limiting each document, so the answer can cite independent evidence.
     */
    private List<RetrievalCandidate> diversify(List<RetrievalCandidate> candidates) {
        int perDocumentLimit = properties.getMaxChunksPerDocument();
        if (perDocumentLimit < 1) return candidates.stream().limit(properties.getTopK()).toList();

        Map<String, Integer> selectedByDocument = new HashMap<>();
        List<RetrievalCandidate> selected = new ArrayList<>();
        for (RetrievalCandidate candidate : candidates) {
            String documentId = candidate.chunk().documentId();
            int selectedCount = selectedByDocument.getOrDefault(documentId, 0);
            if (selectedCount >= perDocumentLimit) continue;
            selected.add(candidate);
            selectedByDocument.put(documentId, selectedCount + 1);
            if (selected.size() == properties.getTopK()) break;
        }
        List<RetrievalCandidate> reranked = new ArrayList<>();
        for (int index = 0; index < selected.size(); index++) {
            RetrievalCandidate candidate = selected.get(index);
            reranked.add(new RetrievalCandidate(candidate.chunk(), candidate.vectorScore(), candidate.vectorRank(),
                    candidate.keywordScore(), candidate.keywordRank(), candidate.rrfScore(), candidate.rerankScore(), index + 1));
        }
        return List.copyOf(reranked);
    }

    private RerankResult rerankOrFallback(String question, List<RetrievalCandidate> candidates) {
        try {
            Map<Integer, Double> scores = rerankerClient.rerank(question, candidates).stream()
                    .filter(hit -> hit.index() < candidates.size())
                    .collect(java.util.stream.Collectors.toMap(RerankHit::index, RerankHit::score, (left, right) -> left));
            if (scores.isEmpty()) throw new RerankerUnavailableException("reranker returned no usable scores");
            List<RetrievalCandidate> ranked = new ArrayList<>();
            for (int index = 0; index < candidates.size(); index++) {
                RetrievalCandidate candidate = candidates.get(index);
                Double score = scores.get(index);
                if (score != null) ranked.add(new RetrievalCandidate(candidate.chunk(), candidate.vectorScore(), candidate.vectorRank(),
                        candidate.keywordScore(), candidate.keywordRank(), candidate.rrfScore(), score, 0));
            }
            ranked.sort(Comparator.comparingDouble(RetrievalCandidate::finalScore).reversed()
                    .thenComparing(RetrievalCandidate::chunkId));
            List<RetrievalCandidate> result = new ArrayList<>();
            for (int index = 0; index < ranked.size(); index++) {
                RetrievalCandidate candidate = ranked.get(index);
                result.add(new RetrievalCandidate(candidate.chunk(), candidate.vectorScore(), candidate.vectorRank(), candidate.keywordScore(),
                        candidate.keywordRank(), candidate.rrfScore(), candidate.rerankScore(), index + 1));
            }
            return new RerankResult(List.copyOf(result), true);
        } catch (RerankerUnavailableException exception) {
            LOGGER.warning("Reranker is unavailable; falling back to hybrid retrieval: " + exception.getMessage());
            return new RerankResult(candidates, false);
        }
    }

    private record RerankResult(List<RetrievalCandidate> candidates, boolean applied) { }
}
