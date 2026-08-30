package com.lingmou.deepfake.rag.index;

import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.config.RagPathResolver;
import com.lingmou.deepfake.rag.ingest.RagChunker;
import com.lingmou.deepfake.rag.ingest.RagDocument;
import com.lingmou.deepfake.rag.ingest.RagDocumentScanner;
import com.lingmou.deepfake.rag.keyword.LuceneBm25Index;
import com.lingmou.deepfake.rag.model.RagChunk;
import com.lingmou.deepfake.rag.vector.VectorStore;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class RagIndexService {
    private final RagProperties properties;
    private final KnowledgeSourceCatalog sourceCatalog;
    private final RagDocumentScanner scanner;
    private final RagChunker chunker;
    private final RagIndexManifestStore manifestStore;
    private final LuceneBm25Index keywordIndex;
    private final VectorStore vectorStore;
    private final RagPathResolver pathResolver;

    public RagIndexService(RagProperties properties, KnowledgeSourceCatalog sourceCatalog, RagDocumentScanner scanner,
            RagChunker chunker, RagIndexManifestStore manifestStore, LuceneBm25Index keywordIndex, VectorStore vectorStore,
            RagPathResolver pathResolver) {
        this.properties = properties;
        this.sourceCatalog = sourceCatalog;
        this.scanner = scanner;
        this.chunker = chunker;
        this.manifestStore = manifestStore;
        this.keywordIndex = keywordIndex;
        this.vectorStore = vectorStore;
        this.pathResolver = pathResolver;
    }

    public synchronized RagIndexStatus status() throws IOException {
        RagIndexManifest manifest = manifestStore.load(indexPath());
        int sourceCount = sourceCatalog.load().size();
        int chunks = manifest.documents().values().stream().mapToInt(entry -> entry.chunkIds().size()).sum();
        return new RagIndexStatus(!manifest.documents().isEmpty(), manifest.updatedAt(), sourceCount,
                manifest.documents().size(), chunks, indexPath().toString());
    }

    public synchronized RagIndexBuildResult update() throws IOException {
        return build(false);
    }

    public synchronized RagIndexBuildResult rebuild() throws IOException {
        return build(true);
    }

    private RagIndexBuildResult build(boolean fullRebuild) throws IOException {
        if (!properties.isEnabled()) {
            throw new IllegalStateException("RAG is disabled by configuration");
        }
        List<KnowledgeSource> sources = sourceCatalog.load();
        List<RagDocument> documents = scanner.scan(knowledgeRoot(), sources);
        Map<RagDocument, List<RagChunk>> current = new LinkedHashMap<>();
        for (RagDocument document : documents) {
            current.put(document, chunker.chunk(document, properties.getChunkSize(), properties.getChunkOverlap()));
        }
        RagIndexManifest previous = manifestStore.load(indexPath());
        IndexChanges changes = manifestStore.changes(previous, current);

        if (fullRebuild) {
            for (DocumentManifestEntry existing : previous.documents().values()) {
                vectorStore.deleteByDocumentId(existing.documentId());
                keywordIndex.deleteDocument(luceneIndexPath(), existing.documentId());
            }
            for (Map.Entry<RagDocument, List<RagChunk>> item : current.entrySet()) {
                vectorStore.upsert(item.getValue());
                keywordIndex.replaceDocument(luceneIndexPath(), item.getKey().documentId(), item.getValue());
            }
        } else {
            for (DocumentManifestEntry deleted : changes.deleted()) {
                vectorStore.deleteByDocumentId(deleted.documentId());
                keywordIndex.deleteDocument(luceneIndexPath(), deleted.documentId());
            }
            for (DocumentManifestEntry changed : changes.addedOrChanged()) {
                RagDocument document = documents.stream()
                        .filter(candidate -> candidate.documentId().equals(changed.documentId()))
                        .findFirst().orElseThrow();
                List<RagChunk> chunks = current.get(document);
                vectorStore.deleteByDocumentId(document.documentId());
                vectorStore.upsert(chunks);
                keywordIndex.replaceDocument(luceneIndexPath(), document.documentId(), chunks);
            }
        }
        manifestStore.save(indexPath(), current);
        int indexedChunks = fullRebuild
                ? current.values().stream().mapToInt(List::size).sum()
                : changes.addedOrChanged().stream().mapToInt(entry -> entry.chunkIds().size()).sum();
        return new RagIndexBuildResult(fullRebuild, Instant.now(), sources.size(), changes.addedOrChanged().size(),
                changes.unchanged().size(), changes.deleted().size(), indexedChunks);
    }

    private Path knowledgeRoot() {
        return pathResolver.resolve(properties.getKnowledgeBasePath());
    }

    private Path indexPath() {
        return pathResolver.resolve(properties.getIndexPath());
    }

    private Path luceneIndexPath() {
        return indexPath().resolve("lucene");
    }
}
