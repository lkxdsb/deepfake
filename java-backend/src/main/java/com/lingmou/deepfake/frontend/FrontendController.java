package com.lingmou.deepfake.frontend;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class FrontendController {
    @GetMapping({
        "/",
        "/welcome",
        "/detect/{kind:image|video|audio}",
        "/results/{taskId}",
        "/history",
        "/history/{taskId}",
        "/chat",
        "/education",
        "/knowledge",
        "/quiz"
    })
    public String frontend() {
        return "forward:/index.html";
    }
}
