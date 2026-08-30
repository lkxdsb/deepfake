#!/usr/bin/env python3
"""Recompute retrieval metrics from recorded raw details after a reviewed-gold update.

It does not issue HTTP requests and does not modify the original details file.
"""
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_eval", HERE / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--details", type=Path, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cases = {case["id"]: case for case in run_eval.load_dataset(args.dataset)}
    previous = [json.loads(line) for line in args.details.read_text(encoding="utf-8").splitlines() if line.strip()]
    rescored = []
    for row in previous:
        case = cases[row["id"]]
        if "error" in row:
            rescored.append(row); continue
        response = {"sources": row.get("sources", []), "answer": row.get("answer"), "model": row.get("model"),
                    "retrievalMode": row.get("reportedRetrievalMode"), "refused": row.get("responseRefused")}
        rescored.append(run_eval.score_case(case, response, row["retrievalLatencyMs"], (1, 3, 5), endpoint="retrieval"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    run_eval.write_jsonl(args.output_dir / f"{args.mode.lower().replace('_', '-')}-details.jsonl", rescored)
    successful = [row for row in rescored if "error" not in row]
    summary = run_eval.summarize(successful, (1, 3, 5), latency_key="retrievalLatencyMs")
    summary.update({"mode": args.mode, "failedCases": len(rescored) - len(successful), "rescored": True})
    (args.output_dir / "comparison.csv").write_text(",".join(summary.keys()) + "\n" + ",".join(str(value) for value in summary.values()) + "\n", encoding="utf-8")
    report = "\n".join([
        "# RAG 离线评测结果（复核金标后重算）", "",
        f"- 原始检索明细：`{args.details}`", f"- 当前人工复核集：`{args.dataset}`",
        "- 说明：本报告只重算指标；不发起新的 HTTP 请求，不改变任何原始检索结果。", "",
        "| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR | 候选引用准确率 | 引用覆盖率 | 知识库路由准确率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| {args.mode} | {summary['recallAt1']:.4f} | {summary['recallAt3']:.4f} | {summary['recallAt5']:.4f} | {summary['mrr']:.4f} | {summary['citationPrecision']:.4f} | {summary['citationCoverage']:.4f} | {summary['knowledgeBaseRoutingAccuracy']:.4f} |",
    ])
    (args.output_dir / "summary.md").write_text(report + "\n", encoding="utf-8")
    print(args.output_dir)
    return 0

if __name__ == "__main__": raise SystemExit(main())
