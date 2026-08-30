package com.lingmou.deepfake.rag.index;

import java.util.List;

public record KnowledgeSourceManifest(int version, List<KnowledgeSource> sources) {
    public KnowledgeSourceManifest {
        sources = sources == null ? List.of() : List.copyOf(sources);
    }
}
