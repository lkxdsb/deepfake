#!/usr/bin/env python3
"""Repeatable, dependency-free offline evaluator for the Java RAG HTTP API.

It never creates expected answers from a model: datasets are committed JSONL and
must be reviewed by a person before they are marked as acceptance data.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MODES = ("VECTOR", "HYBRID", "HYBRID_RERANK")


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def load_dataset(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        record = json.loads(raw)
        required = {"id", "question", "relevantChunkIds", "relevantSources", "shouldRefuse"}
        missing = required - record.keys()
        if missing:
            raise ValueError(f"{path}:{line_number} missing: {sorted(missing)}")
        if record["id"] in seen:
            raise ValueError(f"{path}:{line_number} duplicate id: {record['id']}")
        if not isinstance(record["shouldRefuse"], bool):
            raise ValueError(f"{path}:{line_number} shouldRefuse must be boolean")
        seen.add(record["id"])
        records.append(record)
    if not records:
        raise ValueError("dataset has no cases")
    return records


def post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {body[:500]}") from error


def is_relevant(source: dict[str, Any], case: dict[str, Any]) -> bool:
    # A chunk-id match is the strict primary judgement. Source path is a
    # documented fallback only for legacy cases where a later rebuild changed
    # IDs; such cases must be labelled in dataset review notes.
    return source.get("chunkId") in set(case["relevantChunkIds"])


def score_case(case: dict[str, Any], response: dict[str, Any], latency_ms: float, cutoffs: tuple[int, ...], *, endpoint: str) -> dict[str, Any]:
    sources = response.get("sources") or response.get("hits") or []
    relevant_ranks = [index + 1 for index, source in enumerate(sources) if is_relevant(source, case)]
    first_rank = relevant_ranks[0] if relevant_ranks else None
    should_refuse = case["shouldRefuse"]
    # In this project "shouldRefuse" means no knowledge-base citation should
    # be attached. The product is allowed to provide an explicitly source-free
    # general LLM answer, so this deliberately does NOT score response.refused.
    routing_correct = (not sources) if should_refuse else bool(first_rank)
    return {
        "id": case["id"], "question": case["question"], "shouldRefuse": should_refuse,
        "relevantChunkIds": case["relevantChunkIds"], "relevantSources": case["relevantSources"],
        "answerPoints": case.get("answerPoints", []), "answer": response.get("answer"),
        "model": response.get("model"), "reportedRetrievalMode": response.get("retrievalMode"),
        "responseRefused": response.get("refused"), "sources": sources,
        "firstRelevantRank": first_rank, "routingCorrect": routing_correct,
        f"{endpoint}LatencyMs": round(latency_ms, 3),
        **{f"recallAt{k}": bool(first_rank and first_rank <= k) for k in cutoffs},
    }


def summarize(details: list[dict[str, Any]], cutoffs: tuple[int, ...], *, latency_key: str) -> dict[str, Any]:
    answerable = [detail for detail in details if not detail["shouldRefuse"]]
    sources = [source for detail in details for source in detail["sources"]]
    relevant_citations = sum(
        1 for detail in details for source in detail["sources"]
        if source.get("chunkId") in set(detail["relevantChunkIds"]))
    latency = [detail[latency_key] for detail in details]
    result: dict[str, Any] = {
        "cases": len(details), "answerableCases": len(answerable),
        "knowledgeBaseRoutingAccuracy": sum(d["routingCorrect"] for d in details) / len(details),
        "citationPrecision": relevant_citations / len(sources) if sources else None,
        "citationCoverage": sum(bool(d["firstRelevantRank"]) for d in answerable) / len(answerable) if answerable else None,
        "mrr": sum(1 / d["firstRelevantRank"] if d["firstRelevantRank"] else 0 for d in answerable) / len(answerable) if answerable else None,
        f"{latency_key[:-2]}P50Ms": percentile(latency, .50), f"{latency_key[:-2]}P95Ms": percentile(latency, .95),
    }
    for cutoff in cutoffs:
        result[f"recallAt{cutoff}"] = (sum(d[f"recallAt{cutoff}"] for d in answerable) / len(answerable)) if answerable else None
    return result


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--modes", nargs="+", choices=DEFAULT_MODES, default=list(DEFAULT_MODES))
    parser.add_argument("--cutoffs", nargs="+", type=int, default=[1, 3, 5])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--include-answer", action="store_true", help="also call /api/chat/ask; default measures retrieval only")
    args = parser.parse_args()
    cases, cutoffs = load_dataset(args.dataset), tuple(sorted(set(args.cutoffs)))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    output_dir = args.output_dir or Path("rag-eval/results") / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    summaries: list[dict[str, Any]] = []
    for mode in args.modes:
        details: list[dict[str, Any]] = []
        for case in cases:
            try:
                endpoint = "endToEnd" if args.include_answer else "retrieval"
                url = "/api/chat/ask" if args.include_answer else "/api/rag/retrieve"
                response, latency = post_json(args.base_url.rstrip("/") + url,
                                              {"question": case["question"], "history": [], "retrievalMode": mode}, args.timeout)
                if not args.include_answer:
                    response = response.get("data", response)
                details.append(score_case(case, response, latency, cutoffs, endpoint=endpoint))
            except Exception as error:  # Keep failure as an auditable per-case result.
                details.append({"id": case["id"], "question": case["question"], "error": str(error), f"{('endToEnd' if args.include_answer else 'retrieval')}LatencyMs": None})
        write_jsonl(output_dir / f"{mode.lower().replace('_', '-')}-details.jsonl", details)
        successful = [detail for detail in details if "error" not in detail]
        latency_key = "endToEndLatencyMs" if args.include_answer else "retrievalLatencyMs"
        summary = summarize(successful, cutoffs, latency_key=latency_key) if successful else {"cases": 0}
        summary.update({"mode": mode, "failedCases": len(details) - len(successful)})
        summaries.append(summary)
    columns = sorted({key for row in summaries for key in row})
    with (output_dir / "comparison.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader(); writer.writerows(summaries)
    latency_label = "端到端" if args.include_answer else "检索"
    lines = ["# RAG 离线评测结果", "", f"- 数据集：`{args.dataset}`", f"- 生成时间（UTC）：`{stamp}`", f"- 延迟口径：{latency_label} HTTP 延迟。", "", "| 模式 | Cases | Recall@1 | Recall@3 | Recall@5 | MRR | 引用准确率 | 引用覆盖率 | 知识库路由准确率 | P50 ms | P95 ms |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    def fmt(value: Any) -> str: return "-" if value is None else (f"{value:.4f}" if isinstance(value, float) else str(value))
    for row in summaries:
        latency_prefix = "endToEndLatency" if args.include_answer else "retrievalLatency"
        lines.append("| " + " | ".join(fmt(row.get(key)) for key in ("mode", "cases", "recallAt1", "recallAt3", "recallAt5", "mrr", "citationPrecision", "citationCoverage", "knowledgeBaseRoutingAccuracy", latency_prefix + "P50Ms", latency_prefix + "P95Ms")) + " |")
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_dir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
