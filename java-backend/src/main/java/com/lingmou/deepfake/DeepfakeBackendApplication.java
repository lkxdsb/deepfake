package com.lingmou.deepfake;

import com.lingmou.deepfake.config.DeepfakeProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(DeepfakeProperties.class)
public class DeepfakeBackendApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeepfakeBackendApplication.class, args);
    }
}
