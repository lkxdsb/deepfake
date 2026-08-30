package com.lingmou.deepfake.rag.rerank;

public class RerankerUnavailableException extends RuntimeException {
    public RerankerUnavailableException(String message) { super(message); }
    public RerankerUnavailableException(String message, Throwable cause) { super(message, cause); }
}
