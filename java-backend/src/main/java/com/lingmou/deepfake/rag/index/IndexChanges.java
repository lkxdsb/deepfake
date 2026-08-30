package com.lingmou.deepfake.rag.index;

import java.util.List;

public record IndexChanges(
        List<DocumentManifestEntry> addedOrChanged,
        List<DocumentManifestEntry> unchanged,
        List<DocumentManifestEntry> deleted) {
    public IndexChanges {
        addedOrChanged = List.copyOf(addedOrChanged);
        unchanged = List.copyOf(unchanged);
        deleted = List.copyOf(deleted);
    }
}
