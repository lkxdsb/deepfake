package com.lingmou.deepfake.rag.keyword;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

public interface KeywordRetriever {
    List<KeywordHit> search(Path indexPath, String query, int topK) throws IOException;
}
