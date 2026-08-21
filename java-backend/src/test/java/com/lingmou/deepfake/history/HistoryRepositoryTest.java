package com.lingmou.deepfake.history;

import static org.assertj.core.api.Assertions.assertThat;

import com.lingmou.deepfake.config.DeepfakeProperties;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class HistoryRepositoryTest {
    @TempDir
    Path temporaryDirectory;

    private HistoryRepository repository;

    @BeforeEach
    void setUp() throws Exception {
        DeepfakeProperties properties = new DeepfakeProperties();
        properties.setSqlitePath(temporaryDirectory.resolve("history.db"));
        repository = new HistoryRepository(properties);
        repository.initialize();
    }

    @Test
    void persistsAndAggregatesBatchRecords() {
        repository.save(record("img_1", "real", 0.1, 1));
        repository.save(record("img_2", "fake", 0.9, 2));

        List<Map<String, Object>> batches = repository.listBatches(20);

        assertThat(batches).hasSize(1);
        assertThat(((Number) batches.getFirst().get("item_count")).intValue()).isEqualTo(2);
        assertThat(((Number) batches.getFirst().get("fake_count")).intValue()).isEqualTo(1);
        assertThat(repository.findBatch("imgbatch_1")).hasSize(2);
        assertThat(((Number) repository.overallSummary().get("total_samples")).intValue()).isEqualTo(2);
    }

    private DetectionRecord record(String taskId, String label, double score, int index) {
        return new DetectionRecord(
                null,
                taskId,
                taskId + ".jpg",
                "image",
                label,
                score,
                "/tmp/" + taskId + ".jpg",
                "/tmp/" + taskId + ".json",
                null,
                "2026-08-21T15:00:0" + index,
                "test-model",
                0.25,
                "imgbatch_1",
                "test batch",
                2,
                index);
    }
}
