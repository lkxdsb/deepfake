package com.lingmou.deepfake.rag.ingest;

import com.lingmou.deepfake.rag.model.RagChunk;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class RagChunker {
    private static final Pattern HEADING = Pattern.compile("^(#{1,6})\\s+(.+?)\\s*$");

    public List<RagChunk> chunk(RagDocument document, int chunkSize, int overlap) {
        if (chunkSize < 100 || overlap < 0 || overlap >= chunkSize) {
            throw new IllegalArgumentException("chunk size must be at least 100 and overlap must be smaller than chunk size");
        }
        List<RagChunk> chunks = new ArrayList<>();
        int chunkIndex = 0;
        for (Section section : sections(document.content(), document.title())) {
            for (String content : windows(section.content(), chunkSize, overlap)) {
                String contentHash = ChunkIdentity.sha256(content);
                String chunkId = ChunkIdentity.sha256(document.documentId() + "\n" + section.name() + "\n" + chunkIndex + "\n" + contentHash);
                Map<String, String> metadata = new LinkedHashMap<>();
                metadata.put("documentId", document.documentId());
                metadata.put("path", document.relativePath());
                metadata.put("title", document.title());
                metadata.put("section", section.name());
                metadata.put("chunkIndex", Integer.toString(chunkIndex));
                chunks.add(new RagChunk(chunkId, document.documentId(), document.title(), document.relativePath(),
                        section.name(), chunkIndex++, content, contentHash, metadata));
            }
        }
        return List.copyOf(chunks);
    }

    private List<Section> sections(String content, String fallbackTitle) {
        List<Section> sections = new ArrayList<>();
        String currentName = fallbackTitle;
        StringBuilder currentContent = new StringBuilder();
        for (String line : content.split("\\n", -1)) {
            Matcher match = HEADING.matcher(line);
            if (match.matches()) {
                addSection(sections, currentName, currentContent);
                currentName = match.group(2).strip();
                currentContent.setLength(0);
            } else {
                currentContent.append(line).append('\n');
            }
        }
        addSection(sections, currentName, currentContent);
        return sections;
    }

    private void addSection(List<Section> sections, String name, StringBuilder content) {
        String text = content.toString().strip();
        if (!text.isBlank()) {
            sections.add(new Section(name, text));
        }
    }

    private List<String> windows(String text, int chunkSize, int overlap) {
        List<String> windows = new ArrayList<>();
        int start = 0;
        while (start < text.length()) {
            start = skipLowSurrogate(text, start);
            int hardEnd = Math.min(text.length(), start + chunkSize);
            hardEnd = avoidSplittingSurrogatePair(text, start, hardEnd);
            int end = hardEnd == text.length() ? hardEnd : preferredBoundary(text, start, hardEnd);
            String window = text.substring(start, end).strip();
            if (!window.isBlank()) {
                windows.add(window);
            }
            if (end >= text.length()) {
                break;
            }
            start = skipLowSurrogate(text, Math.max(start + 1, end - overlap));
        }
        return windows;
    }

    private int avoidSplittingSurrogatePair(String text, int start, int end) {
        if (end > start && end < text.length() && Character.isHighSurrogate(text.charAt(end - 1))
                && Character.isLowSurrogate(text.charAt(end))) {
            return end - 1;
        }
        return end;
    }

    private int skipLowSurrogate(String text, int index) {
        return index > 0 && index < text.length() && Character.isLowSurrogate(text.charAt(index))
                && Character.isHighSurrogate(text.charAt(index - 1)) ? index + 1 : index;
    }

    private int preferredBoundary(String text, int start, int hardEnd) {
        int minimum = start + Math.max(1, (hardEnd - start) * 2 / 3);
        for (int index = hardEnd; index > minimum; index--) {
            char value = text.charAt(index - 1);
            if (value == '\n' || Character.isWhitespace(value) || value == '。' || value == '.' || value == '！' || value == '？') {
                return index;
            }
        }
        return hardEnd;
    }

    private record Section(String name, String content) {
    }
}
