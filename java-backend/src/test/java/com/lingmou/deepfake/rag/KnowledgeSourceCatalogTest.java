package com.lingmou.deepfake.rag;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.config.RagPathResolver;
import com.lingmou.deepfake.rag.index.KnowledgeSourceCatalog;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class KnowledgeSourceCatalogTest {
    @Test
    void loadsReviewedProjectSources() throws Exception {
        RagProperties properties = new RagProperties();
        properties.setKnowledgeBasePath(Path.of(".."));
        properties.setSourceManifest(Path.of("../knowledge-base/sources.json"));

        assertThat(new KnowledgeSourceCatalog(properties, new ObjectMapper(), new RagPathResolver()).load()).isNotEmpty();
    }
}
