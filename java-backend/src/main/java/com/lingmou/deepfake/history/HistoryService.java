package com.lingmou.deepfake.history;

import com.fasterxml.jackson.databind.JsonNode;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.storage.FileStorageService;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class HistoryService {
    private final HistoryRepository repository;
    private final FileStorageService storage;

    public HistoryService(HistoryRepository repository, FileStorageService storage) {
        this.repository = repository;
        this.storage = storage;
    }

    public List<Map<String, Object>> list(int limit) {
        List<Map<String, Object>> rows = repository.listBatches(limit);
        rows.forEach(this::addSuspiciousRate);
        return rows;
    }

    public Map<String, Object> detail(String taskId) {
        List<Map<String, Object>> rows = resolveBatch(taskId);
        List<Map<String, Object>> items = rows.stream().map(row -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("result", storage.readResult(Path.of(stringValue(row, "result_json_path"))));
            item.put("record", publicRecord(row));
            return item;
        }).toList();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("batch", batchSummary(rows));
        result.put("items", items);
        return result;
    }

    public Map<String, Object> analytics(String taskId) {
        List<Map<String, Object>> rows = resolveBatch(taskId);
        int itemCount = rows.size();
        int fakeCount = (int) rows.stream().filter(row -> "fake".equals(row.get("result_label"))).count();
        double average = rows.stream().mapToDouble(row -> doubleValue(row, "score")).average().orElse(0.0);

        List<Map<String, Object>> normalized = rows.stream().map(row -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("task_id", row.get("task_id"));
            item.put("file_name", row.get("file_name"));
            item.put("label", row.get("result_label"));
            item.put("score", doubleValue(row, "score"));
            item.put("inference_time", doubleValue(row, "inference_time"));
            item.put("batch_index", intValue(row, "batch_index"));
            return item;
        }).toList();

        List<Map<String, Object>> topRisk = new ArrayList<>(normalized);
        topRisk.sort(Comparator.comparingDouble(row -> -doubleValue(row, "score")));
        topRisk = topRisk.stream().limit(5).toList();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("item_count", itemCount);
        result.put("fake_count", fakeCount);
        result.put("real_count", itemCount - fakeCount);
        result.put("avg_score", average);
        result.put("suspicious_rate", itemCount == 0 ? 0.0 : (double) fakeCount / itemCount);
        result.put("verdict_share", List.of(
                Map.of("name", "Fake", "label", "fake", "value", fakeCount),
                Map.of("name", "Real", "label", "real", "value", itemCount - fakeCount)));
        result.put("score_histogram", histogram(normalized, 10));
        result.put("top_risk_samples", topRisk);
        result.put("summary_text", conclusion(itemCount, fakeCount, average, topRisk));
        return result;
    }

    public Map<String, Object> summary(int recentLimit) {
        Map<String, Object> overall = repository.overallSummary();
        int totalTasks = intValue(overall, "total_tasks");
        int totalSamples = intValue(overall, "total_samples");
        int totalFake = intValue(overall, "total_fake_samples");

        List<Map<String, Object>> recent = repository.listBatches(recentLimit);
        java.util.Collections.reverse(recent);
        for (int index = 0; index < recent.size(); index++) {
            addSuspiciousRate(recent.get(index));
            recent.get(index).put("short_label", "#" + (index + 1));
        }

        List<Map<String, Object>> modalities = repository.modalitySummary();
        for (Map<String, Object> row : modalities) {
            int count = intValue(row, "item_count");
            int fake = intValue(row, "fake_count");
            row.put("real_count", Math.max(count - fake, 0));
            row.put("suspicious_rate", count == 0 ? 0.0 : (double) fake / count);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total_tasks", totalTasks);
        result.put("total_samples", totalSamples);
        result.put("total_fake_samples", totalFake);
        result.put("total_real_samples", Math.max(totalSamples - totalFake, 0));
        result.put("overall_suspicious_rate", totalSamples == 0 ? 0.0 : (double) totalFake / totalSamples);
        result.put("latest_created_at", overall.get("latest_created_at"));
        result.put("recent_batches", recent);
        result.put("modalities", modalities);
        return result;
    }

    private List<Map<String, Object>> resolveBatch(String taskId) {
        Map<String, Object> record = repository.findRecord(taskId).orElse(null);
        String batchId = record == null ? taskId : stringValue(record, "batch_task_id");
        List<Map<String, Object>> rows = repository.findBatch(batchId);
        if (rows.isEmpty() && record == null) {
            throw new ApiException(HttpStatus.NOT_FOUND, "task not found");
        }
        return rows.isEmpty() ? List.of(record) : rows;
    }

    private Map<String, Object> batchSummary(List<Map<String, Object>> rows) {
        Map<String, Object> first = rows.getFirst();
        int fakeCount = (int) rows.stream().filter(row -> "fake".equals(row.get("result_label"))).count();
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("task_id", first.get("batch_task_id"));
        summary.put("batch_name", first.get("batch_name"));
        summary.put("file_type", first.get("file_type"));
        summary.put("item_count", rows.size());
        summary.put("fake_count", fakeCount);
        summary.put("avg_score", rows.stream().mapToDouble(row -> doubleValue(row, "score")).average().orElse(0.0));
        summary.put("total_inference_time", rows.stream().mapToDouble(row -> doubleValue(row, "inference_time")).sum());
        summary.put("created_at", rows.stream().map(row -> stringValue(row, "created_at")).min(String::compareTo).orElse(""));
        summary.put("suspicious_rate", (double) fakeCount / rows.size());
        return summary;
    }

    private Map<String, Object> publicRecord(Map<String, Object> row) {
        Map<String, Object> record = new LinkedHashMap<>(row);
        record.remove("source_path");
        record.remove("result_json_path");
        record.remove("preview_path");
        return record;
    }

    private List<Map<String, Object>> histogram(List<Map<String, Object>> rows, int bins) {
        int[] counts = new int[bins];
        for (Map<String, Object> row : rows) {
            double score = Math.max(0.0, Math.min(0.999999, doubleValue(row, "score")));
            counts[Math.min((int) Math.floor(score * bins), bins - 1)]++;
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (int index = 0; index < bins; index++) {
            double start = (double) index / bins;
            double end = (double) (index + 1) / bins;
            result.add(Map.of(
                    "label", "%.1f-%.1f".formatted(start, end),
                    "count", counts[index], "start", start, "end", end));
        }
        return result;
    }

    private String conclusion(int itemCount, int fakeCount, double average, List<Map<String, Object>> topRisk) {
        double rate = itemCount == 0 ? 0.0 : (double) fakeCount / itemCount;
        String level = rate >= 0.6 || average >= 0.75 ? "整体风险偏高"
                : rate >= 0.25 || average >= 0.55 ? "整体风险中等"
                : fakeCount > 0 ? "存在少量可疑样本" : "整体结果偏稳定";
        String text = "当前批次共 %d 个样本，其中 %d 个被判定为可疑，可疑率 %.1f%%，平均风险分 %.3f，%s。"
                .formatted(itemCount, fakeCount, rate * 100, average, level);
        if (!topRisk.isEmpty()) {
            Map<String, Object> top = topRisk.getFirst();
            text += " 最高风险样本为 %s，风险分 %.3f。"
                    .formatted(top.get("file_name"), doubleValue(top, "score"));
        }
        return text;
    }

    private void addSuspiciousRate(Map<String, Object> row) {
        int itemCount = intValue(row, "item_count");
        int fakeCount = intValue(row, "fake_count");
        row.put("suspicious_rate", itemCount == 0 ? 0.0 : (double) fakeCount / itemCount);
    }

    static int intValue(Map<String, Object> row, String key) {
        Object value = row.get(key);
        return value instanceof Number number ? number.intValue() : 0;
    }

    static double doubleValue(Map<String, Object> row, String key) {
        Object value = row.get(key);
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    static String stringValue(Map<String, Object> row, String key) {
        Object value = row.get(key);
        return value == null ? "" : value.toString();
    }
}
