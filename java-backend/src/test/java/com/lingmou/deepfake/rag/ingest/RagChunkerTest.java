package com.lingmou.deepfake.rag.ingest;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.rag.model.RagChunk;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class RagChunkerTest {
    private final RagChunker chunker = new RagChunker();

    @Test
    void createsStableIdsAndKeepsSectionMetadata() {
        String content = "# 灵眸鉴真\n前言内容。\n\n## 视频检测\n" + "视频检测说明。".repeat(80);
        RagDocument document = new RagDocument("doc-1", Path.of("docs/video.md"), "docs/video.md",
                "灵眸鉴真", content, "content-hash");

        List<RagChunk> first = chunker.chunk(document, 160, 30);
        List<RagChunk> second = chunker.chunk(document, 160, 30);

        assertThat(first).hasSizeGreaterThan(2);
        assertThat(first).extracting(RagChunk::chunkId).containsExactlyElementsOf(second.stream().map(RagChunk::chunkId).toList());
        assertThat(first).allSatisfy(chunk -> {
            assertThat(chunk.chunkId()).hasSize(64);
            assertThat(chunk.metadata()).containsEntry("path", "docs/video.md");
        });
        assertThat(first).anySatisfy(chunk -> assertThat(chunk.section()).isEqualTo("视频检测"));
    }

    @Test
    void preservesConfiguredOverlapBetweenWindows() {
        String content = "# 标题\n" + "abcdefghijklmnopqrstuvwxyz ".repeat(20);
        RagDocument document = new RagDocument("doc-1", Path.of("guide.md"), "guide.md", "标题", content, "hash");

        List<RagChunk> chunks = chunker.chunk(document, 120, 40);

        assertThat(chunks).hasSizeGreaterThan(1);
        String suffix = chunks.get(0).content().substring(chunks.get(0).content().length() - 20);
        assertThat(chunks.get(1).content()).contains(suffix.trim());
    }

    @Test
    void doesNotSplitSupplementaryCharactersAtChunkBoundaries() {
        String content = "# 标题\n" + "a".repeat(94) + "😀" + "b".repeat(120);
        RagDocument document = new RagDocument("doc-emoji", Path.of("emoji.md"), "emoji.md", "标题", content, "hash");

        List<RagChunk> chunks = chunker.chunk(document, 100, 10);

        assertThat(chunks).hasSizeGreaterThan(1);
        assertThat(chunks).allSatisfy(chunk -> assertThat(hasOnlyValidSurrogatePairs(chunk.content())).isTrue());
    }

    private boolean hasOnlyValidSurrogatePairs(String value) {
        for (int index = 0; index < value.length(); index++) {
            char current = value.charAt(index);
            if (Character.isHighSurrogate(current)) {
                if (index + 1 == value.length() || !Character.isLowSurrogate(value.charAt(++index))) return false;
            } else if (Character.isLowSurrogate(current)) {
                return false;
            }
        }
        return true;
    }
}
