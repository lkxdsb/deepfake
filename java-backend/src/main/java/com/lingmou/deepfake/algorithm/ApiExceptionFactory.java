package com.lingmou.deepfake.algorithm;

import com.lingmou.deepfake.api.ApiException;
import org.springframework.http.HttpStatus;

final class ApiExceptionFactory {
    private ApiExceptionFactory() {
    }

    static ApiException algorithmUnavailable(Exception exception) {
        return new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "algorithm service unavailable");
    }

    static ApiException invalidAlgorithmResponse(String detail) {
        return new ApiException(HttpStatus.BAD_GATEWAY, "invalid algorithm response: " + detail);
    }
}
