package com.lingmou.deepfake;

import com.lingmou.deepfake.config.DeepfakeProperties;
import com.lingmou.deepfake.rag.config.RagProperties;
import java.nio.file.Path;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({DeepfakeProperties.class, RagProperties.class})
public class DeepfakeBackendApplication {
    public static void main(String[] args) {
        System.setProperty("deepfake.application-root", Path.of("").toAbsolutePath().normalize().toString());
        SpringApplication.run(DeepfakeBackendApplication.class, args);
    }
}
