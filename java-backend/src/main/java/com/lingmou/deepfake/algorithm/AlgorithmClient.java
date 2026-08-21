package com.lingmou.deepfake.algorithm;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lingmou.deepfake.detection.MediaKind;
import java.nio.file.Path;

public interface AlgorithmClient {
    ObjectNode detect(MediaKind kind, Path mediaPath, String taskId);

    ObjectNode health();
}
