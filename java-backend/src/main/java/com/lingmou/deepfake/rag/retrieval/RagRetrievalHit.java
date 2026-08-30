package com.lingmou.deepfake.rag.retrieval;

/** Retrieval metadata only; full chunk text remains in the indexed local corpus. */
public record RagRetrievalHit(
        String chunkId,
        String title,
        String path,
        String section,
        int finalRank,
        double finalScore,
        Double vectorScore,
        Integer vectorRank,
        Double keywordScore,
        Integer keywordRank,
        Double rrfScore,
        Double rerankScore) {
}
