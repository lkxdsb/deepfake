package com.lingmou.deepfake.chat;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record ChatMessage(
        @Pattern(regexp = "user|assistant") String role,
        @NotBlank @Size(max = 2000) String content) {
}
