package com.lingmou.deepfake.history;

import com.lingmou.deepfake.api.ApiResponse;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/history")
public class HistoryController {
    private final HistoryService historyService;

    public HistoryController(HistoryService historyService) {
        this.historyService = historyService;
    }

    @GetMapping
    public ApiResponse<List<Map<String, Object>>> list() {
        return ApiResponse.success(historyService.list(200));
    }

    @GetMapping("/summary")
    public ApiResponse<Map<String, Object>> summary() {
        return ApiResponse.success(historyService.summary(20));
    }

    @GetMapping("/{taskId}/analytics")
    public ApiResponse<Map<String, Object>> analytics(@PathVariable String taskId) {
        return ApiResponse.success(historyService.analytics(taskId));
    }

    @GetMapping("/{taskId}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable String taskId) {
        return ApiResponse.success(historyService.detail(taskId));
    }
}
