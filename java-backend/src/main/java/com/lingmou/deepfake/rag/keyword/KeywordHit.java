package com.lingmou.deepfake.rag.keyword;

import com.lingmou.deepfake.rag.model.RagChunk;

public record KeywordHit(RagChunk chunk, double score, int rank) {
}
