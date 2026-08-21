package com.lingmou.deepfake.detection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.algorithm.AlgorithmClient;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.history.DetectionRecord;
import com.lingmou.deepfake.history.HistoryRepository;
import com.lingmou.deepfake.storage.FileStorageService;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class DetectionService {
    private final AlgorithmClient algorithmClient;
    private final FileStorageService storage;
    private final HistoryRepository historyRepository;
    private final ObjectMapper objectMapper;
    private final int maxBatchFiles;

    public DetectionService(
            AlgorithmClient algorithmClient,
            FileStorageService storage,
            HistoryRepository historyRepository,
            ObjectMapper objectMapper,
            DeepfakeProperties properties) {
        this.algorithmClient = algorithmClient;
        this.storage = storage;
        this.historyRepository = historyRepository;
        this.objectMapper = objectMapper;
        this.maxBatchFiles = Math.max(1, properties.getMaxBatchFiles());
    }

    public ObjectNode detect(MediaKind kind, List<MultipartFile> uploads, String requestedBatchName) {
        List<MultipartFile> files = uploads.stream().filter(file -> file != null && !file.isEmpty()).toList();
        if (files.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, kind.name().toLowerCase() + " file is required");
        }
        if (files.size() > maxBatchFiles) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "too many files; maximum is " + maxBatchFiles);
        }

        String batchTaskId = files.size() > 1 ? taskId(kind.taskPrefix() + "batch") : null;
        String batchName = resolveBatchName(kind, files.size(), requestedBatchName);
        List<ObjectNode> results = new ArrayList<>();
        List<DetectionRecord> records = new ArrayList<>();
        List<Path> artifacts = new ArrayList<>();

        try {
            for (int index = 0; index < files.size(); index++) {
                MultipartFile upload = files.get(index);
                String taskId = taskId(kind.taskPrefix());
                Path source = storage.saveUpload(upload, kind, taskId);
                artifacts.add(source);
                ObjectNode result = algorithmClient.detect(kind, source, taskId);
                normalizeResult(
                        result,
                        kind,
                        taskId,
                        upload.getOriginalFilename(),
                        batchTaskId == null ? taskId : batchTaskId,
                        batchName == null ? upload.getOriginalFilename() : batchName,
                        files.size(),
                        index + 1);
                Path resultPath = storage.saveResult(taskId, result);
                artifacts.add(resultPath);
                records.add(historyRecord(result, source, resultPath));
                results.add(result);
            }
            historyRepository.saveAll(records);
        } catch (RuntimeException exception) {
            artifacts.forEach(storage::deleteArtifact);
            throw exception;
        }

        return results.size() == 1 ? results.getFirst() : batchResponse(results, batchTaskId, batchName, kind);
    }

    private void normalizeResult(
            ObjectNode result,
            MediaKind kind,
            String taskId,
            String filename,
            String batchTaskId,
            String batchName,
            int batchSize,
            int batchIndex) {
        validateVerdict(result);
        result.put("task_id", taskId);
        result.put("file_name", filename == null ? "upload" : filename);
        result.put("file_type", kind.name().toLowerCase());
        result.put("batch_task_id", batchTaskId);
        result.put("batch_name", batchName == null ? filename : batchName);
        result.put("batch_size", batchSize);
        result.put("batch_index", batchIndex);
        if (!result.has("inference_time")) {
            result.put("inference_time", 0.0);
        }
        if (!result.has("model_name")) {
            result.put("model_name", result.path("modelName").asText("unknown"));
        }
    }

    private DetectionRecord historyRecord(ObjectNode result, Path source, Path resultPath) {
        String preview = firstText(result, "preview_path", "preview_url", "preview_video_url");
        return new DetectionRecord(
                null,
                result.path("task_id").asText(),
                result.path("file_name").asText(),
                result.path("file_type").asText(),
                result.path("label").asText(),
                result.path("score").asDouble(),
                source.toAbsolutePath().toString(),
                resultPath.toAbsolutePath().toString(),
                preview,
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                result.path("model_name").asText("unknown"),
                result.path("inference_time").asDouble(),
                result.path("batch_task_id").asText(),
                result.path("batch_name").asText(),
                result.path("batch_size").asInt(1),
                result.path("batch_index").asInt(1));
    }

    private ObjectNode batchResponse(
            List<ObjectNode> results, String batchTaskId, String batchName, MediaKind kind) {
        ObjectNode response = objectMapper.createObjectNode();
        response.put("batch_task_id", batchTaskId);
        response.put("batch_name", batchName);
        response.put("batch_size", results.size());
        response.put("file_type", kind.name().toLowerCase());
        ArrayNode taskIds = response.putArray("task_ids");
        ArrayNode items = response.putArray("items");
        for (ObjectNode result : results) {
            taskIds.add(result.path("task_id").asText());
            ObjectNode item = items.addObject();
            item.put("task_id", result.path("task_id").asText());
            item.put("file_name", result.path("file_name").asText());
            item.put("label", result.path("label").asText());
            item.put("score", result.path("score").asDouble());
        }
        return response;
    }

    private String resolveBatchName(MediaKind kind, int count, String requested) {
        if (requested != null && !requested.isBlank()) {
            String normalized = requested.strip();
            if (normalized.length() > 80 || normalized.chars().anyMatch(Character::isISOControl)) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "invalid batch name");
            }
            return normalized;
        }
        if (count <= 1) {
            return null;
        }
        return kind.displayName() + "批量任务 " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("MM-dd HH:mm"));
    }

    private void require(ObjectNode result, String field) {
        if (!result.hasNonNull(field)) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "algorithm response missing field: " + field);
        }
    }

    private void validateVerdict(ObjectNode result) {
        require(result, "label");
        require(result, "score");
        if (!result.path("label").isTextual()) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "algorithm response has invalid label");
        }
        String label = result.path("label").asText().toLowerCase();
        if (!Set.of("real", "fake").contains(label)) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "algorithm response has invalid label");
        }
        if (!result.path("score").isNumber()) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "algorithm response has invalid score");
        }
        double score = result.path("score").asDouble();
        if (!Double.isFinite(score) || score < 0.0 || score > 1.0) {
            throw new ApiException(HttpStatus.BAD_GATEWAY, "algorithm response has invalid score");
        }
        result.put("label", label);
        result.put("score", score);
    }

    private String firstText(ObjectNode result, String... fields) {
        for (String field : fields) {
            if (result.hasNonNull(field) && !result.path(field).asText().isBlank()) {
                return result.path(field).asText();
            }
        }
        return null;
    }

    private String taskId(String prefix) {
        return prefix + "_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}
