package com.lingmou.deepfake.history;

public record DetectionRecord(
        Long id,
        String taskId,
        String fileName,
        String fileType,
        String resultLabel,
        double score,
        String sourcePath,
        String resultJsonPath,
        String previewPath,
        String createdAt,
        String modelVersion,
        double inferenceTime,
        String batchTaskId,
        String batchName,
        int batchSize,
        int batchIndex) {
}
