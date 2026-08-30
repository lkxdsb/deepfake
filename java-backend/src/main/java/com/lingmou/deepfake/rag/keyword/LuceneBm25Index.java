package com.lingmou.deepfake.rag.keyword;

import com.lingmou.deepfake.rag.model.RagChunk;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StoredField;
import org.apache.lucene.document.StringField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.Term;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;
import org.springframework.stereotype.Component;

@Component
public class LuceneBm25Index implements KeywordRetriever {
    private static final String FIELD_CHUNK_ID = "chunkId";
    private static final String FIELD_DOCUMENT_ID = "documentId";
    private static final String FIELD_TITLE = "title";
    private static final String FIELD_PATH = "path";
    private static final String FIELD_SECTION = "section";
    private static final String FIELD_CHUNK_INDEX = "chunkIndex";
    private static final String FIELD_CONTENT = "content";
    private static final String FIELD_CONTENT_HASH = "contentHash";

    public void replaceDocument(Path indexPath, String documentId, Collection<RagChunk> chunks) throws IOException {
        Files.createDirectories(indexPath);
        try (Directory directory = FSDirectory.open(indexPath);
             StandardAnalyzer analyzer = new StandardAnalyzer();
             IndexWriter writer = new IndexWriter(directory, writerConfig(analyzer))) {
            writer.deleteDocuments(new Term(FIELD_DOCUMENT_ID, documentId));
            for (RagChunk chunk : chunks) {
                if (!documentId.equals(chunk.documentId())) {
                    throw new IllegalArgumentException("chunk document ID does not match requested replacement");
                }
                writer.addDocument(toDocument(chunk));
            }
            writer.commit();
        }
    }

    public void deleteDocument(Path indexPath, String documentId) throws IOException {
        if (!Files.exists(indexPath)) {
            return;
        }
        try (Directory directory = FSDirectory.open(indexPath);
             StandardAnalyzer analyzer = new StandardAnalyzer();
             IndexWriter writer = new IndexWriter(directory, writerConfig(analyzer))) {
            writer.deleteDocuments(new Term(FIELD_DOCUMENT_ID, documentId));
            writer.commit();
        }
    }

    @Override
    public List<KeywordHit> search(Path indexPath, String query, int topK) throws IOException {
        if (query == null || query.isBlank() || topK < 1 || !Files.exists(indexPath)) {
            return List.of();
        }
        try (Directory directory = FSDirectory.open(indexPath)) {
            if (!DirectoryReader.indexExists(directory)) {
                return List.of();
            }
            try (DirectoryReader reader = DirectoryReader.open(directory); StandardAnalyzer analyzer = new StandardAnalyzer()) {
                Query parsed = new QueryParser(FIELD_CONTENT, analyzer).parse(QueryParser.escape(query.strip()));
                IndexSearcher searcher = new IndexSearcher(reader);
                searcher.setSimilarity(new BM25Similarity());
                TopDocs results = searcher.search(parsed, topK);
                List<KeywordHit> hits = new ArrayList<>();
                int rank = 1;
                for (ScoreDoc scoreDoc : results.scoreDocs) {
                    hits.add(new KeywordHit(fromDocument(searcher.storedFields().document(scoreDoc.doc)), scoreDoc.score, rank++));
                }
                return List.copyOf(hits);
            } catch (org.apache.lucene.queryparser.classic.ParseException exception) {
                throw new IllegalArgumentException("invalid keyword query", exception);
            }
        }
    }

    private IndexWriterConfig writerConfig(StandardAnalyzer analyzer) {
        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        config.setSimilarity(new BM25Similarity());
        return config;
    }

    private Document toDocument(RagChunk chunk) {
        Document document = new Document();
        document.add(new StringField(FIELD_CHUNK_ID, chunk.chunkId(), Field.Store.YES));
        document.add(new StringField(FIELD_DOCUMENT_ID, chunk.documentId(), Field.Store.YES));
        document.add(new StoredField(FIELD_TITLE, chunk.title()));
        document.add(new StoredField(FIELD_PATH, chunk.path()));
        document.add(new StoredField(FIELD_SECTION, chunk.section()));
        document.add(new StoredField(FIELD_CHUNK_INDEX, chunk.chunkIndex()));
        document.add(new TextField(FIELD_CONTENT, chunk.content(), Field.Store.YES));
        document.add(new StoredField(FIELD_CONTENT_HASH, chunk.contentHash()));
        return document;
    }

    private RagChunk fromDocument(Document document) {
        Map<String, String> metadata = new LinkedHashMap<>();
        metadata.put("documentId", document.get(FIELD_DOCUMENT_ID));
        metadata.put("title", document.get(FIELD_TITLE));
        metadata.put("path", document.get(FIELD_PATH));
        metadata.put("section", document.get(FIELD_SECTION));
        metadata.put("chunkIndex", document.get(FIELD_CHUNK_INDEX));
        return new RagChunk(document.get(FIELD_CHUNK_ID), document.get(FIELD_DOCUMENT_ID), document.get(FIELD_TITLE),
                document.get(FIELD_PATH), document.get(FIELD_SECTION), Integer.parseInt(document.get(FIELD_CHUNK_INDEX)),
                document.get(FIELD_CONTENT), document.get(FIELD_CONTENT_HASH), metadata);
    }
}
