package com.lingmou.deepfake.detection;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.api.ApiResponse;
import java.util.ArrayList;
import java.util.List;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/detect")
public class DetectionController {
    private final DetectionService detectionService;

    public DetectionController(DetectionService detectionService) {
        this.detectionService = detectionService;
    }

    @PostMapping("/image")
    public ApiResponse<ObjectNode> detectImage(
            @RequestParam(required = false) MultipartFile file,
            @RequestParam(required = false) List<MultipartFile> files,
            @RequestParam(required = false, name = "batch_name") String batchName) {
        return detect(MediaKind.IMAGE, file, files, batchName);
    }

    @PostMapping("/video")
    public ApiResponse<ObjectNode> detectVideo(
            @RequestParam(required = false) MultipartFile file,
            @RequestParam(required = false) List<MultipartFile> files,
            @RequestParam(required = false, name = "batch_name") String batchName) {
        return detect(MediaKind.VIDEO, file, files, batchName);
    }

    @PostMapping("/audio")
    public ApiResponse<ObjectNode> detectAudio(
            @RequestParam(required = false) MultipartFile file,
            @RequestParam(required = false) List<MultipartFile> files,
            @RequestParam(required = false, name = "batch_name") String batchName) {
        return detect(MediaKind.AUDIO, file, files, batchName);
    }

    private ApiResponse<ObjectNode> detect(
            MediaKind kind,
            MultipartFile file,
            List<MultipartFile> files,
            String batchName) {
        List<MultipartFile> uploads = new ArrayList<>();
        if (file != null) {
            uploads.add(file);
        }
        if (files != null) {
            uploads.addAll(files);
        }
        return ApiResponse.success(detectionService.detect(kind, uploads, batchName));
    }
}
