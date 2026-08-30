import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_eval", Path(__file__).with_name("run_eval.py"))
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)

class MetricsTest(unittest.TestCase):
    def test_reviewed_dataset_has_auditable_chunk_ids(self):
        root = Path(__file__).parent.parent
        cases = run_eval.load_dataset(root / "rag-eval/datasets/rag-v1-manually-reviewed.jsonl")
        manifest = json.loads((root / "rag-index/manifest.json").read_text(encoding="utf-8"))
        chunk_ids = {chunk_id for document in manifest["documents"].values() for chunk_id in document["chunkIds"]}
        self.assertGreaterEqual(len(cases), 100)
        self.assertTrue(all(
            case["shouldRefuse"] or set(case["relevantChunkIds"]).issubset(chunk_ids)
            for case in cases
        ))

    def test_recall_mrr_and_citation_metrics(self):
        cases = [
            {"id":"a", "question":"q", "relevantChunkIds":["c1"], "relevantSources":["x"], "shouldRefuse":False},
            {"id":"b", "question":"q", "relevantChunkIds":["c2"], "relevantSources":["y"], "shouldRefuse":False},
        ]
        responses = [
            {"sources":[{"chunkId":"c1"},{"chunkId":"wrong"}]},
            {"sources":[{"chunkId":"wrong"},{"chunkId":"c2"}]},
        ]
        details = [run_eval.score_case(case, response, 10, (1, 3, 5), endpoint="retrieval") for case, response in zip(cases, responses)]
        result = run_eval.summarize(details, (1, 3, 5), latency_key="retrievalLatencyMs")
        self.assertEqual(0.5, result["recallAt1"])
        self.assertEqual(1.0, result["recallAt3"])
        self.assertEqual(0.75, result["mrr"])
        self.assertEqual(0.5, result["citationPrecision"])
        self.assertEqual(1.0, result["citationCoverage"])

    def test_source_free_general_chat_is_correct_for_out_of_kb_case(self):
        case = {"id":"o", "question":"q", "relevantChunkIds":[], "relevantSources":[], "shouldRefuse":True}
        detail = run_eval.score_case(case, {"answer":"普通回答", "sources":[], "refused":False}, 10, (1,), endpoint="endToEnd")
        self.assertTrue(detail["routingCorrect"])

if __name__ == "__main__":
    unittest.main()
