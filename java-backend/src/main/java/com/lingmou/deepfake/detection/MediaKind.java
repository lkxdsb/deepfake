package com.lingmou.deepfake.detection;

import java.util.Locale;
import java.util.Set;

public enum MediaKind {
    IMAGE("img", "图片", Set.of(".jpg", ".jpeg", ".png")),
    VIDEO("vid", "视频", Set.of(".mp4", ".avi", ".mov", ".mkv")),
    AUDIO("aud", "音频", Set.of(".wav", ".mp3", ".flac"));

    private final String taskPrefix;
    private final String displayName;
    private final Set<String> extensions;

    MediaKind(String taskPrefix, String displayName, Set<String> extensions) {
        this.taskPrefix = taskPrefix;
        this.displayName = displayName;
        this.extensions = extensions;
    }

    public String taskPrefix() {
        return taskPrefix;
    }

    public String displayName() {
        return displayName;
    }

    public boolean supports(String filename) {
        String lower = filename.toLowerCase(Locale.ROOT);
        return extensions.stream().anyMatch(lower::endsWith);
    }
}
