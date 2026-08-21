package com.lingmou.deepfake.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.api.ApiException;
import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.detection.MediaKind;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;

class FileStorageServiceTest {
    @TempDir
    Path temporaryDirectory;

    private FileStorageService storage;

    @BeforeEach
    void setUp() throws Exception {
        DeepfakeProperties properties = new DeepfakeProperties();
        properties.setOutputRoot(temporaryDirectory.resolve("outputs"));
        storage = new FileStorageService(properties, new ObjectMapper());
        storage.prepareDirectories();
    }

    @Test
    void storesSupportedImageWithSafeName() throws Exception {
        MockMultipartFile upload = new MockMultipartFile(
                "file", "../person face.jpg", "image/jpeg", new byte[] {1, 2, 3});

        Path stored = storage.saveUpload(upload, MediaKind.IMAGE, "img_123");

        assertThat(stored.getFileName().toString()).isEqualTo("img_123_person_face.jpg");
        assertThat(Files.readAllBytes(stored)).containsExactly(1, 2, 3);
    }

    @Test
    void rejectsUnsupportedExtension() {
        MockMultipartFile upload = new MockMultipartFile(
                "file", "payload.exe", "application/octet-stream", new byte[] {1});

        assertThatThrownBy(() -> storage.saveUpload(upload, MediaKind.IMAGE, "img_123"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("unsupported image format");
    }
}
