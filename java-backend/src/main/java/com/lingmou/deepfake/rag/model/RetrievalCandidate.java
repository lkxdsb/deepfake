package com.lingmou.deepfake.rag.model;

public record RetrievalCandidate(
        RagChunk chunk,
        Double vectorScore,
        Integer vectorRank,
        Double keywordScore,
        Integer keywordRank,
        Double rrfScore,
        Double rerankScore,
        int finalRank) {
    public String chunkId() {
        return chunk.chunkId();
    }

    public double finalScore() {
        if (rerankScore != null) return rerankScore;
        if (rrfScore != null) return rrfScore;
        if (vectorScore != null) return vectorScore;
        return keywordScore == null ? 0.0 : keywordScore;
    }
}
