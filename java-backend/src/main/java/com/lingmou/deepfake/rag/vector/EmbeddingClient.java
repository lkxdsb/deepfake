package com.lingmou.deepfake.rag.vector;

import java.util.List;

public interface EmbeddingClient {
    List<List<Double>> embed(List<String> inputs);
}
