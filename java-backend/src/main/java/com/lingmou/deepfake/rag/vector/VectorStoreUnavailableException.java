package com.lingmou.deepfake.rag.vector;

public class VectorStoreUnavailableException extends RuntimeException {
    public VectorStoreUnavailableException(String message) { super(message); }
    public VectorStoreUnavailableException(String message, Throwable cause) { super(message, cause); }
}
