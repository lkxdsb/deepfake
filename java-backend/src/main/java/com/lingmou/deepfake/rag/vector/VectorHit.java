package com.lingmou.deepfake.rag.vector;

import com.lingmou.deepfake.rag.model.RagChunk;

public record VectorHit(RagChunk chunk, double score, int rank, double distance) {
}
