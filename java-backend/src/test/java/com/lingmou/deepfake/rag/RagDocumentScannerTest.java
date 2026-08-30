package com.lingmou.deepfake.rag;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.rag.index.KnowledgeSource;
import com.lingmou.deepfake.rag.ingest.RagDocument;
import com.lingmou.deepfake.rag.ingest.RagDocumentScanner;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class RagDocumentScannerTest {
    @TempDir
    Path directory;

    @Test
    void readsOnlyReviewedSourcesAndConvertsLatexSections() throws Exception {
        Files.writeString(directory.resolve("method.tex"), "\\section{CASE}\nA \\textbf{method} for video detection.");
        Files.writeString(directory.resolve("unreviewed.md"), "# Do not import");

        List<RagDocument> documents = new RagDocumentScanner().scan(directory,
                List.of(new KnowledgeSource("method.tex", "paper", "CASE method", null)));

        assertThat(documents).hasSize(1);
        assertThat(documents.getFirst().title()).isEqualTo("CASE method");
        assertThat(documents.getFirst().content()).contains("## CASE").contains("A method");
    }

    @Test
    void removesMalformedSurrogatesFromImportedText() {
        String normalized = RagDocumentScanner.sanitizeUnicode("正常\uD83D文本\uDC00，保留 😀。");

        assertThat(normalized).isEqualTo("正常文本，保留 😀。");
    }
}
