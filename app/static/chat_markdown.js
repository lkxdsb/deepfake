(() => {
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderInline(text) {
    let html = escapeHtml(text);
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    return html;
  }

  function isTableSeparator(line) {
    return /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line);
  }

  function splitTableRow(line) {
    let normalized = line.trim();
    if (normalized.startsWith("|")) {
      normalized = normalized.slice(1);
    }
    if (normalized.endsWith("|")) {
      normalized = normalized.slice(0, -1);
    }
    return normalized.split("|").map((cell) => cell.trim());
  }

  function buildTable(headers, rows) {
    const thead = `<thead><tr>${headers.map((cell) => `<th>${renderInline(cell)}</th>`).join("")}</tr></thead>`;
    const tbody = `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`).join("")}</tbody>`;
    return `<div class="chat-rich__table"><table>${thead}${tbody}</table></div>`;
  }

  function renderMarkdown(markdown) {
    const source = String(markdown || "").replace(/\r\n?/g, "\n").trim();
    if (!source) {
      return "";
    }

    const lines = source.split("\n");
    const blocks = [];
    let paragraph = [];
    let index = 0;

    function flushParagraph() {
      if (!paragraph.length) {
        return;
      }
      blocks.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }

    while (index < lines.length) {
      const line = lines[index];
      const trimmed = line.trim();

      if (!trimmed) {
        flushParagraph();
        index += 1;
        continue;
      }

      if (trimmed.startsWith("```")) {
        flushParagraph();
        const codeLines = [];
        index += 1;
        while (index < lines.length && !lines[index].trim().startsWith("```")) {
          codeLines.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) {
          index += 1;
        }
        blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        continue;
      }

      const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
      if (headingMatch) {
        flushParagraph();
        const level = Math.min(headingMatch[1].length + 1, 4);
        blocks.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
        index += 1;
        continue;
      }

      if (trimmed.startsWith(">")) {
        flushParagraph();
        const quoteLines = [];
        while (index < lines.length && lines[index].trim().startsWith(">")) {
          quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
          index += 1;
        }
        blocks.push(`<blockquote><p>${renderInline(quoteLines.join(" "))}</p></blockquote>`);
        continue;
      }

      if (trimmed.includes("|") && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
        flushParagraph();
        const headers = splitTableRow(trimmed);
        index += 2;
        const rows = [];
        while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
          rows.push(splitTableRow(lines[index]));
          index += 1;
        }
        blocks.push(buildTable(headers, rows));
        continue;
      }

      const unorderedMatch = trimmed.match(/^[-*+]\s+(.*)$/);
      if (unorderedMatch) {
        flushParagraph();
        const items = [];
        while (index < lines.length) {
          const match = lines[index].trim().match(/^[-*+]\s+(.*)$/);
          if (!match) {
            break;
          }
          items.push(match[1]);
          index += 1;
        }
        blocks.push(`<ul>${items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>`);
        continue;
      }

      const orderedMatch = trimmed.match(/^\d+\.\s+(.*)$/);
      if (orderedMatch) {
        flushParagraph();
        const items = [];
        while (index < lines.length) {
          const match = lines[index].trim().match(/^\d+\.\s+(.*)$/);
          if (!match) {
            break;
          }
          items.push(match[1]);
          index += 1;
        }
        blocks.push(`<ol>${items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ol>`);
        continue;
      }

      paragraph.push(trimmed);
      index += 1;
    }

    flushParagraph();
    return blocks.join("");
  }

  function renderInto(container, text, options = {}) {
    const markdown = options.markdown !== false;
    if (!markdown) {
      container.textContent = String(text || "");
      return;
    }
    container.innerHTML = renderMarkdown(text);
  }

  window.DeepfakeChat = {
    renderInto,
    renderMarkdown,
  };
})();
