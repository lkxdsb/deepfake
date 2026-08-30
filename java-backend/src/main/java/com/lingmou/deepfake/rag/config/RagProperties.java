package com.lingmou.deepfake.rag.config;

import com.lingmou.deepfake.rag.model.RetrievalMode;
import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "deepfake.rag")
public class RagProperties {
    private boolean enabled = true;
    private Path knowledgeBasePath = Path.of(".");
    private Path indexPath = Path.of("rag-index");
    private Path sourceManifest = Path.of("knowledge-base/sources.json");
    private int chunkSize = 800;
    private int chunkOverlap = 120;
    private int topK = 5;
    /** Number of highest-ranked chunks exposed to the answer model and user as citations. */
    private int answerSourceK = 2;
    private int rerankCandidateK = 20;
    private int rrfK = 60;
    private int maxChunksPerDocument = 2;
    private double minVectorScore = 0.47;
    private double refusalThreshold = 0.01;
    private RetrievalMode defaultRetrievalMode = RetrievalMode.HYBRID_RERANK;
    private final Chroma chroma = new Chroma();
    private final Embedding embedding = new Embedding();
    private final Reranker reranker = new Reranker();

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public Path getKnowledgeBasePath() { return knowledgeBasePath; }
    public void setKnowledgeBasePath(Path knowledgeBasePath) { this.knowledgeBasePath = knowledgeBasePath; }
    public Path getIndexPath() { return indexPath; }
    public void setIndexPath(Path indexPath) { this.indexPath = indexPath; }
    public Path getSourceManifest() { return sourceManifest; }
    public void setSourceManifest(Path sourceManifest) { this.sourceManifest = sourceManifest; }
    public int getChunkSize() { return chunkSize; }
    public void setChunkSize(int chunkSize) { this.chunkSize = chunkSize; }
    public int getChunkOverlap() { return chunkOverlap; }
    public void setChunkOverlap(int chunkOverlap) { this.chunkOverlap = chunkOverlap; }
    public int getTopK() { return topK; }
    public void setTopK(int topK) { this.topK = topK; }
    public int getAnswerSourceK() { return answerSourceK; }
    public void setAnswerSourceK(int answerSourceK) { this.answerSourceK = answerSourceK; }
    public int getRerankCandidateK() { return rerankCandidateK; }
    public void setRerankCandidateK(int rerankCandidateK) { this.rerankCandidateK = rerankCandidateK; }
    public int getRrfK() { return rrfK; }
    public void setRrfK(int rrfK) { this.rrfK = rrfK; }
    public int getMaxChunksPerDocument() { return maxChunksPerDocument; }
    public void setMaxChunksPerDocument(int maxChunksPerDocument) { this.maxChunksPerDocument = maxChunksPerDocument; }
    public double getMinVectorScore() { return minVectorScore; }
    public void setMinVectorScore(double minVectorScore) { this.minVectorScore = minVectorScore; }
    public double getRefusalThreshold() { return refusalThreshold; }
    public void setRefusalThreshold(double refusalThreshold) { this.refusalThreshold = refusalThreshold; }
    public RetrievalMode getDefaultRetrievalMode() { return defaultRetrievalMode; }
    public void setDefaultRetrievalMode(RetrievalMode defaultRetrievalMode) { this.defaultRetrievalMode = defaultRetrievalMode; }
    public Chroma getChroma() { return chroma; }
    public Embedding getEmbedding() { return embedding; }
    public Reranker getReranker() { return reranker; }

    public static class Chroma {
        private String baseUrl = "http://127.0.0.1:8001";
        private String collection = "lingmou-rag";
        private String tenant = "default_tenant";
        private String database = "default_database";
        private String authToken;
        private int connectTimeoutSeconds = 5;
        private int readTimeoutSeconds = 30;
        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public String getCollection() { return collection; }
        public void setCollection(String collection) { this.collection = collection; }
        public String getTenant() { return tenant; }
        public void setTenant(String tenant) { this.tenant = tenant; }
        public String getDatabase() { return database; }
        public void setDatabase(String database) { this.database = database; }
        public String getAuthToken() { return authToken; }
        public void setAuthToken(String authToken) { this.authToken = authToken; }
        public int getConnectTimeoutSeconds() { return connectTimeoutSeconds; }
        public void setConnectTimeoutSeconds(int connectTimeoutSeconds) { this.connectTimeoutSeconds = connectTimeoutSeconds; }
        public int getReadTimeoutSeconds() { return readTimeoutSeconds; }
        public void setReadTimeoutSeconds(int readTimeoutSeconds) { this.readTimeoutSeconds = readTimeoutSeconds; }
    }

    public static class Embedding {
        private String baseUrl;
        private String apiKey;
        private String model = "text-embedding-3-small";
        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public String getApiKey() { return apiKey; }
        public void setApiKey(String apiKey) { this.apiKey = apiKey; }
        public String getModel() { return model; }
        public void setModel(String model) { this.model = model; }
    }

    public static class Reranker {
        private boolean enabled;
        private String baseUrl;
        private String model = "BAAI/bge-reranker-v2-m3";
        private int timeoutSeconds = 15;
        private int maxBatchCandidates = 4;
        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public String getModel() { return model; }
        public void setModel(String model) { this.model = model; }
        public int getTimeoutSeconds() { return timeoutSeconds; }
        public void setTimeoutSeconds(int timeoutSeconds) { this.timeoutSeconds = timeoutSeconds; }
        public int getMaxBatchCandidates() { return maxBatchCandidates; }
        public void setMaxBatchCandidates(int maxBatchCandidates) { this.maxBatchCandidates = maxBatchCandidates; }
    }
}
