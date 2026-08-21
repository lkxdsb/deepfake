package com.lingmou.deepfake.history;

import com.lingmou.deepfake.config.DeepfakeProperties;
import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Repository;

@Repository
public class HistoryRepository {
    private final Path databasePath;
    private String jdbcUrl;

    public HistoryRepository(DeepfakeProperties properties) {
        this.databasePath = properties.getSqlitePath().toAbsolutePath().normalize();
    }

    @PostConstruct
    synchronized void initialize() throws IOException, SQLException {
        Path parent = databasePath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        jdbcUrl = "jdbc:sqlite:" + databasePath;
        try (Connection connection = open(); Statement statement = connection.createStatement()) {
            statement.execute("""
                    CREATE TABLE IF NOT EXISTS detection_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        result_label TEXT NOT NULL,
                        score REAL NOT NULL,
                        source_path TEXT NOT NULL,
                        result_json_path TEXT NOT NULL,
                        preview_path TEXT,
                        created_at TEXT NOT NULL,
                        model_version TEXT NOT NULL,
                        inference_time REAL NOT NULL,
                        batch_task_id TEXT NOT NULL,
                        batch_name TEXT NOT NULL,
                        batch_size INTEGER NOT NULL DEFAULT 1,
                        batch_index INTEGER NOT NULL DEFAULT 1
                    )
                    """);
            statement.execute("CREATE INDEX IF NOT EXISTS idx_detection_batch ON detection_records(batch_task_id)");
            statement.execute("CREATE INDEX IF NOT EXISTS idx_detection_created ON detection_records(created_at)");
        }
    }

    public synchronized void save(DetectionRecord record) {
        saveAll(List.of(record));
    }

    public synchronized void saveAll(List<DetectionRecord> records) {
        if (records.isEmpty()) {
            return;
        }
        String sql = """
                INSERT INTO detection_records (
                    task_id, file_name, file_type, result_label, score, source_path,
                    result_json_path, preview_path, created_at, model_version,
                    inference_time, batch_task_id, batch_name, batch_size, batch_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """;
        try (Connection connection = open()) {
            connection.setAutoCommit(false);
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                for (DetectionRecord record : records) {
                    bindRecord(statement, record);
                    statement.addBatch();
                }
                statement.executeBatch();
                connection.commit();
            } catch (SQLException exception) {
                connection.rollback();
                throw exception;
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Unable to save detection history", exception);
        }
    }

    private void bindRecord(PreparedStatement statement, DetectionRecord record) throws SQLException {
        statement.setString(1, record.taskId());
        statement.setString(2, record.fileName());
        statement.setString(3, record.fileType());
        statement.setString(4, record.resultLabel());
        statement.setDouble(5, record.score());
        statement.setString(6, record.sourcePath());
        statement.setString(7, record.resultJsonPath());
        statement.setString(8, record.previewPath());
        statement.setString(9, record.createdAt());
        statement.setString(10, record.modelVersion());
        statement.setDouble(11, record.inferenceTime());
        statement.setString(12, record.batchTaskId());
        statement.setString(13, record.batchName());
        statement.setInt(14, record.batchSize());
        statement.setInt(15, record.batchIndex());
    }

    public List<Map<String, Object>> listBatches(int limit) {
        String sql = """
                SELECT batch_task_id AS task_id, MAX(batch_name) AS batch_name,
                       MAX(file_type) AS file_type, COUNT(*) AS item_count,
                       SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS fake_count,
                       AVG(score) AS avg_score, SUM(inference_time) AS total_inference_time,
                       MIN(created_at) AS created_at
                FROM detection_records
                GROUP BY batch_task_id
                ORDER BY MAX(id) DESC
                LIMIT ?
                """;
        return query(sql, statement -> statement.setInt(1, Math.max(1, limit)));
    }

    public Optional<Map<String, Object>> findRecord(String taskId) {
        List<Map<String, Object>> rows = query(
                "SELECT * FROM detection_records WHERE task_id = ? LIMIT 1",
                statement -> statement.setString(1, taskId));
        return rows.stream().findFirst();
    }

    public List<Map<String, Object>> findBatch(String batchTaskId) {
        return query(
                "SELECT * FROM detection_records WHERE batch_task_id = ? ORDER BY batch_index ASC, id ASC",
                statement -> statement.setString(1, batchTaskId));
    }

    public Map<String, Object> overallSummary() {
        String sql = """
                SELECT COUNT(DISTINCT batch_task_id) AS total_tasks,
                       COUNT(*) AS total_samples,
                       SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS total_fake_samples,
                       MAX(created_at) AS latest_created_at
                FROM detection_records
                """;
        return query(sql, statement -> { }).stream().findFirst().orElseGet(LinkedHashMap::new);
    }

    public List<Map<String, Object>> modalitySummary() {
        String sql = """
                SELECT file_type, COUNT(DISTINCT batch_task_id) AS batch_count,
                       COUNT(*) AS item_count,
                       SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS fake_count,
                       AVG(inference_time) AS avg_inference_time,
                       SUM(inference_time) AS total_inference_time
                FROM detection_records
                GROUP BY file_type
                ORDER BY file_type ASC
                """;
        return query(sql, statement -> { });
    }

    private List<Map<String, Object>> query(String sql, StatementBinder binder) {
        try (Connection connection = open(); PreparedStatement statement = connection.prepareStatement(sql)) {
            binder.bind(statement);
            try (ResultSet resultSet = statement.executeQuery()) {
                List<Map<String, Object>> rows = new ArrayList<>();
                int columns = resultSet.getMetaData().getColumnCount();
                while (resultSet.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int index = 1; index <= columns; index++) {
                        row.put(resultSet.getMetaData().getColumnLabel(index), resultSet.getObject(index));
                    }
                    rows.add(row);
                }
                return rows;
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Unable to query detection history", exception);
        }
    }

    private Connection open() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    @FunctionalInterface
    private interface StatementBinder {
        void bind(PreparedStatement statement) throws SQLException;
    }
}
