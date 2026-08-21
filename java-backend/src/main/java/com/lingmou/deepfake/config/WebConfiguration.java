package com.lingmou.deepfake.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfiguration implements WebMvcConfigurer {
    private final DeepfakeProperties properties;

    public WebConfiguration(DeepfakeProperties properties) {
        this.properties = properties;
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String outputLocation = properties.getOutputRoot().toAbsolutePath().normalize().toUri().toString();
        registry.addResourceHandler("/outputs/heatmaps/**")
                .addResourceLocations(outputLocation + "heatmaps/");
        registry.addResourceHandler("/outputs/frames/**")
                .addResourceLocations(outputLocation + "frames/");
        registry.addResourceHandler("/outputs/previews/**")
                .addResourceLocations(outputLocation + "previews/");
        registry.addResourceHandler("/outputs/reports/*.png")
                .addResourceLocations(outputLocation + "reports/");
    }
}
