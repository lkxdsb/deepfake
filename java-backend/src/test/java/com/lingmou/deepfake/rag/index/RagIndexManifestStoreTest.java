package com.lingmou.deepfake.rag.index;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.rag.ingest.RagDocument;
import com.lingmou.deepfake.rag.model.RagChunk;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class RagIndexManifestStoreTest {
    @TempDir Path temporaryDirectory;
    private final RagIndexManifestStore store = new RagIndexManifestStore(new ObjectMapper().findAndRegisterModules());

    @Test
    void detectsChangedAndDeletedDocumentsAcrossRuns() throws Exception {
        RagDocument first = document("doc-a", "docs/a.md", "hash-a");
        RagDocument second = document("doc-b", "docs/b.md", "hash-b");
        Map<RagDocument, List<RagChunk>> initial = Map.of(first, List.of(chunk(first, "chunk-a")), second, List.of(chunk(second, "chunk-b")));
        store.save(temporaryDirectory, initial);

        RagIndexManifest manifest = store.load(temporaryDirectory);
        RagDocument changedFirst = document("doc-a", "docs/a.md", "hash-a-new");
        IndexChanges changes = store.changes(manifest, Map.of(changedFirst, List.of(chunk(changedFirst, "chunk-a-new"))));

        assertThat(changes.addedOrChanged()).extracting(DocumentManifestEntry::documentId).containsExactly("doc-a");
        assertThat(changes.deleted()).extracting(DocumentManifestEntry::documentId).containsExactly("doc-b");
        assertThat(changes.unchanged()).isEmpty();
    }

    private RagDocument document(String id, String path, String hash) {
        return new RagDocument(id, Path.of(path), path, path, "text", hash);
    }

    private RagChunk chunk(RagDocument document, String id) {
        return new RagChunk(id, document.documentId(), document.title(), document.relativePath(), "section", 0,
                document.content(), "content", Map.of());
    }
}
