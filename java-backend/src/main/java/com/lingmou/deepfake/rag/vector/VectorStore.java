package com.lingmou.deepfake.rag.vector;

import com.lingmou.deepfake.rag.model.RagChunk;
import java.util.Collection;
import java.util.List;

public interface VectorStore {
    void upsert(Collection<RagChunk> chunks);
    void deleteByDocumentId(String documentId);
    List<VectorHit> search(String question, int topK);
}
