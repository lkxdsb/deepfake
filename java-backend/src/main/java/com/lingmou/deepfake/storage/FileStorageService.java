package com.lingmou.deepfake.storage;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.detection.MediaKind;
import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class FileStorageService {
    private final DeepfakeProperties properties;
    private final ObjectMapper objectMapper;

    public FileStorageService(DeepfakeProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    void prepareDirectories() throws IOException {
        Files.createDirectories(uploadDirectory());
        Files.createDirectories(reportDirectory());
    }

    public Path saveUpload(MultipartFile file, MediaKind kind, String taskId) {
        String originalName = file.getOriginalFilename() == null ? "upload" : file.getOriginalFilename();
        String safeName;
        try {
            safeName = sanitizeFilename(Path.of(originalName).getFileName().toString());
        } catch (InvalidPathException exception) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid filename");
        }
        if (!kind.supports(safeName)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "unsupported " + kind.name().toLowerCase() + " format");
        }
        if (file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, kind.name().toLowerCase() + " file is empty");
        }

        long maxBytes = (long) maxMegabytes(kind) * 1024 * 1024;
        if (file.getSize() > maxBytes) {
            throw new ApiException(HttpStatus.BAD_REQUEST, kind.name().toLowerCase() + " file is too large");
        }

        Path destination = uploadDirectory().resolve(taskId + "_" + safeName).normalize();
        if (!destination.startsWith(uploadDirectory())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid filename");
        }
        try (InputStream input = file.getInputStream()) {
            Files.copy(input, destination, StandardCopyOption.REPLACE_EXISTING);
            return destination;
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "unable to store uploaded file");
        }
    }

    public Path saveResult(String taskId, JsonNode result) {
        Path destination = reportDirectory().resolve(taskId + ".json");
        try {
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(destination.toFile(), result);
            return destination;
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "unable to save detection result");
        }
    }

    public JsonNode readResult(Path path) {
        try {
            return objectMapper.readTree(path.toFile());
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "unable to read detection result");
        }
    }

    public void deleteArtifact(Path path) {
        if (path == null) {
            return;
        }
        Path normalized = path.toAbsolutePath().normalize();
        Path outputRoot = properties.getOutputRoot().toAbsolutePath().normalize();
        if (!normalized.startsWith(outputRoot)) {
            return;
        }
        try {
            Files.deleteIfExists(normalized);
        } catch (IOException ignored) {
            // Cleanup is best effort; the original request error remains the useful failure.
        }
    }

    private String sanitizeFilename(String filename) {
        String normalized = filename.replaceAll("[^A-Za-z0-9._-]", "_");
        normalized = normalized.replaceAll("_+", "_");
        if (normalized.length() > 120) {
            int extensionStart = normalized.lastIndexOf('.');
            String extension = extensionStart >= 0 ? normalized.substring(extensionStart).toLowerCase(Locale.ROOT) : "";
            int basenameLength = Math.max(1, 120 - extension.length());
            normalized = normalized.substring(0, basenameLength) + extension;
        }
        return normalized.isBlank() ? "upload" : normalized;
    }

    private Path uploadDirectory() {
        return properties.getOutputRoot().toAbsolutePath().normalize().resolve("uploads");
    }

    private Path reportDirectory() {
        return properties.getOutputRoot().toAbsolutePath().normalize().resolve("reports");
    }

    private int maxMegabytes(MediaKind kind) {
        return switch (kind) {
            case IMAGE -> properties.getMaxImageMb();
            case VIDEO -> properties.getMaxVideoMb();
            case AUDIO -> properties.getMaxAudioMb();
        };
    }
}
