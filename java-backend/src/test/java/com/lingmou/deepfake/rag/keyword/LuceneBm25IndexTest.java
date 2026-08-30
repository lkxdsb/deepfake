package com.lingmou.deepfake.rag.keyword;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.rag.model.RagChunk;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LuceneBm25IndexTest {
    @TempDir Path temporaryDirectory;
    private final LuceneBm25Index index = new LuceneBm25Index();

    @Test
    void returnsBm25RankedChunkAndReplacesDocumentAtomically() throws Exception {
        RagChunk visual = chunk("visual-1", "doc-visual", "docs/visual.md", "CASE 和 Bi-ST 用于视频深度伪造检测。");
        RagChunk audio = chunk("audio-1", "doc-audio", "docs/audio.md", "XLS-R-2B 用于音频合成内容识别。");
        index.replaceDocument(temporaryDirectory, "doc-visual", List.of(visual));
        index.replaceDocument(temporaryDirectory, "doc-audio", List.of(audio));

        List<KeywordHit> hits = index.search(temporaryDirectory, "CASE Bi-ST 视频", 3);

        assertThat(hits).isNotEmpty();
        assertThat(hits.getFirst().chunk().chunkId()).isEqualTo("visual-1");
        assertThat(hits.getFirst().rank()).isEqualTo(1);

        RagChunk replacement = chunk("visual-2", "doc-visual", "docs/visual.md", "视觉检测改用新的说明。");
        index.replaceDocument(temporaryDirectory, "doc-visual", List.of(replacement));
        assertThat(index.search(temporaryDirectory, "CASE", 3)).isEmpty();
        assertThat(index.search(temporaryDirectory, "视觉", 3)).extracting(hit -> hit.chunk().chunkId()).containsExactly("visual-2");
    }

    @Test
    void returnsNoHitsAfterDocumentDeletion() throws Exception {
        index.replaceDocument(temporaryDirectory, "doc-1", List.of(chunk("chunk-1", "doc-1", "guide.md", "数字取证工作流")));
        index.deleteDocument(temporaryDirectory, "doc-1");

        assertThat(index.search(temporaryDirectory, "数字取证", 3)).isEmpty();
    }

    private RagChunk chunk(String chunkId, String documentId, String path, String content) {
        return new RagChunk(chunkId, documentId, "标题", path, "章节", 0, content, "content-hash", Map.of());
    }
}
