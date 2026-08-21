package com.lingmou.deepfake.config;

import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "deepfake")
public class DeepfakeProperties {
    private Path outputRoot = Path.of("outputs-java");
    private Path sqlitePath = Path.of("outputs-java/app.db");
    private String algorithmBaseUrl = "http://127.0.0.1:8100";
    private int algorithmConnectTimeoutSeconds = 5;
    private int algorithmReadTimeoutSeconds = 900;
    private int maxImageMb = 20;
    private int maxVideoMb = 500;
    private int maxAudioMb = 100;
    private int maxBatchFiles = 20;
    private final Chat chat = new Chat();

    public Path getOutputRoot() {
        return outputRoot;
    }

    public void setOutputRoot(Path outputRoot) {
        this.outputRoot = outputRoot;
    }

    public Path getSqlitePath() {
        return sqlitePath;
    }

    public void setSqlitePath(Path sqlitePath) {
        this.sqlitePath = sqlitePath;
    }

    public String getAlgorithmBaseUrl() {
        return algorithmBaseUrl;
    }

    public void setAlgorithmBaseUrl(String algorithmBaseUrl) {
        this.algorithmBaseUrl = algorithmBaseUrl;
    }

    public int getAlgorithmConnectTimeoutSeconds() {
        return algorithmConnectTimeoutSeconds;
    }

    public void setAlgorithmConnectTimeoutSeconds(int algorithmConnectTimeoutSeconds) {
        this.algorithmConnectTimeoutSeconds = algorithmConnectTimeoutSeconds;
    }

    public int getAlgorithmReadTimeoutSeconds() {
        return algorithmReadTimeoutSeconds;
    }

    public void setAlgorithmReadTimeoutSeconds(int algorithmReadTimeoutSeconds) {
        this.algorithmReadTimeoutSeconds = algorithmReadTimeoutSeconds;
    }

    public int getMaxImageMb() {
        return maxImageMb;
    }

    public void setMaxImageMb(int maxImageMb) {
        this.maxImageMb = maxImageMb;
    }

    public int getMaxVideoMb() {
        return maxVideoMb;
    }

    public void setMaxVideoMb(int maxVideoMb) {
        this.maxVideoMb = maxVideoMb;
    }

    public int getMaxAudioMb() {
        return maxAudioMb;
    }

    public void setMaxAudioMb(int maxAudioMb) {
        this.maxAudioMb = maxAudioMb;
    }

    public int getMaxBatchFiles() {
        return maxBatchFiles;
    }

    public void setMaxBatchFiles(int maxBatchFiles) {
        this.maxBatchFiles = maxBatchFiles;
    }

    public Chat getChat() {
        return chat;
    }

    public static class Chat {
        private String apiKey;
        private String baseUrl = "https://dashscope.aliyuncs.com/compatible-mode/v1";
        private String model = "qwen3.6-plus";
        private double temperature = 0.3;
        private int maxHistoryMessages = 6;
        private int connectTimeoutSeconds = 5;
        private int readTimeoutSeconds = 60;

        public String getApiKey() {
            return apiKey;
        }

        public void setApiKey(String apiKey) {
            this.apiKey = apiKey;
        }

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public String getModel() {
            return model;
        }

        public void setModel(String model) {
            this.model = model;
        }

        public double getTemperature() {
            return temperature;
        }

        public void setTemperature(double temperature) {
            this.temperature = temperature;
        }

        public int getMaxHistoryMessages() {
            return maxHistoryMessages;
        }

        public void setMaxHistoryMessages(int maxHistoryMessages) {
            this.maxHistoryMessages = maxHistoryMessages;
        }

        public int getConnectTimeoutSeconds() {
            return connectTimeoutSeconds;
        }

        public void setConnectTimeoutSeconds(int connectTimeoutSeconds) {
            this.connectTimeoutSeconds = connectTimeoutSeconds;
        }

        public int getReadTimeoutSeconds() {
            return readTimeoutSeconds;
        }

        public void setReadTimeoutSeconds(int readTimeoutSeconds) {
            this.readTimeoutSeconds = readTimeoutSeconds;
        }
    }
}
