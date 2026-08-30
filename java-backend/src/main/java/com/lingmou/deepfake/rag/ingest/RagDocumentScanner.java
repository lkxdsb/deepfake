package com.lingmou.deepfake.rag.ingest;

import com.lingmou.deepfake.rag.index.KnowledgeSource;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Stream;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Component;

@Component
public class RagDocumentScanner {
    private static final Set<String> SUPPORTED_EXTENSIONS = Set.of(".md", ".txt", ".pdf", ".tex");
    private static final Set<String> IGNORED_DIRECTORIES = Set.of(".git", "target", "node_modules", "outputs", "outputs-java", "rag-index");

    public List<RagDocument> scan(Path knowledgeBaseRoot) throws IOException {
        Path root = knowledgeBaseRoot.toAbsolutePath().normalize();
        if (!Files.isDirectory(root)) {
            throw new IOException("knowledge base path is not a directory: " + root);
        }
        try (Stream<Path> paths = Files.walk(root)) {
            return paths
                    .filter(Files::isRegularFile)
                    .filter(path -> !containsIgnoredDirectory(root.relativize(path)))
                    .filter(this::isSupported)
                    .sorted(Comparator.comparing(path -> toRelativePath(root, path)))
                    .map(path -> read(root, path, null))
                    .toList();
        }
    }

    /** Reads only the reviewed entries in the source manifest, rather than every supported file below the root. */
    public List<RagDocument> scan(Path knowledgeBaseRoot, Collection<KnowledgeSource> sources) throws IOException {
        Path root = knowledgeBaseRoot.toAbsolutePath().normalize();
        if (!Files.isDirectory(root)) {
            throw new IOException("knowledge base path is not a directory: " + root);
        }
        return sources.stream()
                .sorted(Comparator.comparing(KnowledgeSource::path))
                .map(source -> {
                    Path path = root.resolve(source.path()).normalize();
                    if (!path.startsWith(root) || !Files.isRegularFile(path) || !isSupported(path)) {
                        throw new IllegalArgumentException("invalid knowledge source: " + source.path());
                    }
                    return read(root, path, source.title());
                })
                .toList();
    }

    private RagDocument read(Path root, Path path, String configuredTitle) {
        try {
            String relativePath = toRelativePath(root, path);
            String content = normalize(readText(path));
            String title = configuredTitle == null || configuredTitle.isBlank()
                    ? title(content, path.getFileName().toString()) : configuredTitle.strip();
            String documentId = ChunkIdentity.sha256(relativePath);
            return new RagDocument(documentId, path, relativePath, title, content, ChunkIdentity.sha256(content));
        } catch (IOException exception) {
            throw new IllegalStateException("unable to read knowledge base document: " + path, exception);
        }
    }

    private boolean isSupported(Path path) {
        String name = path.getFileName().toString().toLowerCase(Locale.ROOT);
        return SUPPORTED_EXTENSIONS.stream().anyMatch(name::endsWith);
    }

    private boolean containsIgnoredDirectory(Path relativePath) {
        for (Path part : relativePath) {
            if (IGNORED_DIRECTORIES.contains(part.toString())) {
                return true;
            }
        }
        return false;
    }

    private String readText(Path path) throws IOException {
        String filename = path.getFileName().toString().toLowerCase(Locale.ROOT);
        if (filename.endsWith(".pdf")) {
            try (PDDocument document = PDDocument.load(path.toFile())) {
                return new PDFTextStripper().getText(document);
            }
        }
        String raw = Files.readString(path, StandardCharsets.UTF_8);
        return filename.endsWith(".tex") ? latexToText(raw) : raw;
    }

    private String latexToText(String latex) {
        String text = latex
                .replaceAll("(?m)^\\\\(?:sub)*section\\*?\\{([^}]*)}", "## $1")
                .replaceAll("(?m)^\\\\paragraph\\{([^}]*)}", "### $1")
                .replaceAll("\\\\(?:textbf|textit|emph|cite|ref|label)\\{([^}]*)}", "$1")
                .replace("~", " ")
                .replace("\\\\_", "_");
        return text.replaceAll("(?m)^%.*$", "");
    }

    private String title(String content, String filename) {
        return content.lines()
                .map(String::strip)
                .filter(line -> line.startsWith("# "))
                .map(line -> line.substring(2).strip())
                .filter(line -> !line.isBlank())
                .findFirst()
                .orElse(filename);
    }

    private String normalize(String content) {
        return sanitizeUnicode(content.replace("\r\n", "\n").replace('\r', '\n')).strip();
    }

    /**
     * PDF text extraction can occasionally yield a dangling UTF-16 surrogate.
     * JSON/Chroma rejects such strings, so remove only malformed code units while
     * preserving valid supplementary characters (for example emoji).
     */
    public static String sanitizeUnicode(String value) {
        StringBuilder sanitized = new StringBuilder(value.length());
        for (int index = 0; index < value.length(); index++) {
            char current = value.charAt(index);
            if (Character.isHighSurrogate(current)) {
                if (index + 1 < value.length() && Character.isLowSurrogate(value.charAt(index + 1))) {
                    sanitized.append(current).append(value.charAt(++index));
                }
            } else if (!Character.isLowSurrogate(current)) {
                sanitized.append(current);
            }
        }
        return sanitized.toString();
    }

    private String toRelativePath(Path root, Path path) {
        return root.relativize(path).toString().replace(path.getFileSystem().getSeparator(), "/");
    }
}
