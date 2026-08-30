package com.lingmou.deepfake.rag.index;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.rag.ingest.RagDocument;
import com.lingmou.deepfake.rag.model.RagChunk;
import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;

@Component
public class RagIndexManifestStore {
    private static final String MANIFEST_FILE = "manifest.json";
    private final ObjectMapper objectMapper;

    public RagIndexManifestStore(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public RagIndexManifest load(Path indexPath) throws IOException {
        Path manifest = indexPath.resolve(MANIFEST_FILE);
        if (!Files.exists(manifest)) {
            return RagIndexManifest.empty();
        }
        return objectMapper.readValue(manifest.toFile(), RagIndexManifest.class);
    }

    public IndexChanges changes(RagIndexManifest previous, Map<RagDocument, List<RagChunk>> current) {
        List<DocumentManifestEntry> changed = new ArrayList<>();
        List<DocumentManifestEntry> unchanged = new ArrayList<>();
        Map<String, DocumentManifestEntry> currentEntries = new LinkedHashMap<>();
        for (Map.Entry<RagDocument, List<RagChunk>> item : current.entrySet()) {
            RagDocument document = item.getKey();
            DocumentManifestEntry entry = new DocumentManifestEntry(document.documentId(), document.relativePath(),
                    document.contentHash(), item.getValue().stream().map(RagChunk::chunkId).toList());
            currentEntries.put(document.documentId(), entry);
            DocumentManifestEntry old = previous.documents().get(document.documentId());
            if (old == null || !old.contentHash().equals(entry.contentHash())) {
                changed.add(entry);
            } else {
                unchanged.add(entry);
            }
        }
        Set<String> currentIds = currentEntries.keySet();
        List<DocumentManifestEntry> deleted = previous.documents().values().stream()
                .filter(entry -> !currentIds.contains(entry.documentId()))
                .toList();
        return new IndexChanges(changed, unchanged, deleted);
    }

    public void save(Path indexPath, Map<RagDocument, List<RagChunk>> documents) throws IOException {
        Files.createDirectories(indexPath);
        Map<String, DocumentManifestEntry> entries = new LinkedHashMap<>();
        for (Map.Entry<RagDocument, List<RagChunk>> item : documents.entrySet()) {
            RagDocument document = item.getKey();
            entries.put(document.documentId(), new DocumentManifestEntry(document.documentId(), document.relativePath(),
                    document.contentHash(), item.getValue().stream().map(RagChunk::chunkId).toList()));
        }
        Path destination = indexPath.resolve(MANIFEST_FILE);
        Path temporary = Files.createTempFile(indexPath, "manifest-", ".json");
        objectMapper.writerWithDefaultPrettyPrinter().writeValue(temporary.toFile(),
                new RagIndexManifest(1, Instant.now(), entries));
        try {
            Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException ignored) {
            Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
