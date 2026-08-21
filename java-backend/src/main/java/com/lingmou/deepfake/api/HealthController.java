package com.lingmou.deepfake.api;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.algorithm.AlgorithmClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class HealthController {
    private final AlgorithmClient algorithmClient;

    public HealthController(AlgorithmClient algorithmClient) {
        this.algorithmClient = algorithmClient;
    }

    @GetMapping("/health")
    public ObjectNode health() {
        ObjectNode health = algorithmClient.health();
        health.put("business_backend", "java");
        return health;
    }
}
