package com.lingmou.deepfake.rag.retrieval;

import com.lingmou.deepfake.api.ApiResponse;
import com.lingmou.deepfake.rag.config.RagProperties;
import com.lingmou.deepfake.rag.model.RetrievalCandidate;
import com.lingmou.deepfake.rag.model.RetrievalMode;
import com.lingmou.deepfake.rag.model.RetrievalResult;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Retrieval-only endpoint for repeatable offline evaluation. It intentionally does not call
 * the chat model, so its latency can be measured separately from answer generation.
 */
@RestController
@RequestMapping("/api/rag/retrieve")
public class RagRetrievalController {
    private final RagRetrievalService retrievalService;
    private final RagProperties properties;

    public RagRetrievalController(RagRetrievalService retrievalService, RagProperties properties) {
        this.retrievalService = retrievalService;
        this.properties = properties;
    }

    @PostMapping
    public ApiResponse<RagRetrievalResponse> retrieve(@Valid @RequestBody RagRetrievalRequest request) {
        RetrievalMode requestedMode = request.retrievalMode() == null
                ? properties.getDefaultRetrievalMode() : request.retrievalMode();
        RetrievalResult result = retrievalService.retrieve(request.question(), requestedMode);
        List<RagRetrievalHit> hits = result.candidates().stream().map(this::toHit).toList();
        return ApiResponse.success(new RagRetrievalResponse(result.mode(), result.valid(), result.rejectionReason(), hits));
    }

    private RagRetrievalHit toHit(RetrievalCandidate candidate) {
        return new RagRetrievalHit(candidate.chunkId(), candidate.chunk().title(), candidate.chunk().path(),
                candidate.chunk().section(), candidate.finalRank(), candidate.finalScore(), candidate.vectorScore(),
                candidate.vectorRank(), candidate.keywordScore(), candidate.keywordRank(), candidate.rrfScore(),
                candidate.rerankScore());
    }
}
