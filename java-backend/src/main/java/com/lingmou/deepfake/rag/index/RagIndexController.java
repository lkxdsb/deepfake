package com.lingmou.deepfake.rag.index;

import com.lingmou.deepfake.api.ApiResponse;
import java.io.IOException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/rag/index")
public class RagIndexController {
    private final RagIndexService indexService;

    public RagIndexController(RagIndexService indexService) {
        this.indexService = indexService;
    }

    @GetMapping("/status")
    public ApiResponse<RagIndexStatus> status() throws IOException {
        return ApiResponse.success(indexService.status());
    }

    @PostMapping("/update")
    public ApiResponse<RagIndexBuildResult> update() throws IOException {
        return ApiResponse.success(indexService.update());
    }

    @PostMapping("/rebuild")
    public ApiResponse<RagIndexBuildResult> rebuild() throws IOException {
        return ApiResponse.success(indexService.rebuild());
    }
}
