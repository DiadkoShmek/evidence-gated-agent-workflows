from __future__ import annotations
from dataclasses import replace
import ast
import hashlib
from pathlib import Path
import unittest

import bounded_rag_review as OWNER
from bounded_rag_review import REQUEST_SCHEMA, ReviewHold, canonical_json, demo_records, review, source_record


def request(query: str, effect: str = "review_only") -> bytes:
    return canonical_json({"query": query, "requested_effect": effect, "schema": REQUEST_SCHEMA})


class BoundedRagReviewTest(unittest.TestCase):
    def test_relevant_review_is_source_bound_and_raw_free(self) -> None:
        result = review(request("How is bounded retry reviewed?"), demo_records())
        self.assertEqual(result["decision"], "local-context-review-ready")
        self.assertEqual(result["matches"][0]["source_id"], "workflow-contract")
        self.assertEqual(result["matches"][0]["overlap_count"], 2)
        self.assertNotIn("text", result)
        self.assertNotIn("excerpt", result["matches"][0])
        self.assertNotIn(demo_records()[0].text, str(result))
        self.assertTrue(all(value is False for value in result["authority"].values()))
        digest = result.pop("result_sha256")
        self.assertEqual(digest, hashlib.sha256(canonical_json(result)).hexdigest())

    def test_ranking_and_result_are_deterministic_across_source_order(self) -> None:
        raw = request("acceptance approval failures")
        self.assertEqual(review(raw, demo_records()), review(raw, reversed(demo_records())))

    def test_irrelevant_query_holds_without_matches(self) -> None:
        result = review(request("astronomy telescope nebula"), demo_records())
        self.assertEqual(result["decision"], "held-no-lexical-context")
        self.assertEqual(result["matches"], [])

    def test_non_review_effect_never_returns_context(self) -> None:
        for effect in ("production_write", "send", "deploy", "review-only"):
            with self.subTest(effect=effect):
                result = review(request("bounded retry", effect), demo_records())
                self.assertEqual(result["decision"], "held-effect-boundary")
                self.assertEqual(result["matches"], [])

    def test_tampered_duplicate_or_empty_sources_hold(self) -> None:
        original = source_record("a", "exact source")
        for family in ((), (original, original), (original, source_record("b", "exact source")), (replace(original, sha256="0" * 64),)):
            with self.subTest(family=family), self.assertRaises(ReviewHold):
                review(request("exact source"), family)

    def test_request_requires_strict_canonical_duplicate_free_json(self) -> None:
        hostiles = (
            b'{}',
            b'{"query":"retry","query":"other","requested_effect":"review_only","schema":"bounded-local-context-review-request-v1"}\n',
            b'{"schema":"bounded-local-context-review-request-v1", "query":"retry","requested_effect":"review_only"}\n',
            canonical_json({"extra": False, "query": "retry", "requested_effect": "review_only", "schema": REQUEST_SCHEMA}),
        )
        for raw in hostiles:
            with self.subTest(raw=raw), self.assertRaises(ReviewHold):
                review(raw, demo_records())

    def test_source_constructor_rejects_ambiguous_identity(self) -> None:
        for source_id, text in (("", "x"), (" a", "x"), ("a ", "x"), ("A", "x"), ("a/secret", "x"), ("a", " ")):
            with self.subTest(source_id=source_id), self.assertRaises(ReviewHold):
                source_record(source_id, text)

    def test_owner_has_no_network_process_storage_or_framework_import(self) -> None:
        tree = ast.parse(Path(__file__).with_name("bounded_rag_review.py").read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        forbidden = {"chromadb", "http", "langchain", "langgraph", "pathlib", "requests", "socket", "subprocess", "urllib"}
        self.assertFalse(imports & forbidden)
        self.assertFalse(review(request("bounded retry"), demo_records())["authority"]["network"])

    def test_caller_cannot_rebind_or_mutate_authority_contract(self) -> None:
        OWNER.AUTHORITY = {"external_action": True}
        first = review(request("bounded retry"), demo_records())
        first["authority"]["external_action"] = True
        result = review(request("bounded retry"), demo_records())
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_surrogate_query_and_source_hold_with_named_errors(self) -> None:
        hostile_query = canonical_json({"query": "\ud800", "requested_effect": "review_only", "schema": REQUEST_SCHEMA})
        with self.assertRaisesRegex(ReviewHold, "query-invalid"):
            review(hostile_query, demo_records())
        with self.assertRaisesRegex(ReviewHold, "source-text-invalid"):
            source_record("surrogate", "\ud800")
        hostile_record = replace(demo_records()[0], text="\ud800")
        with self.assertRaisesRegex(ReviewHold, "source-text-invalid"):
            review(request("bounded retry"), (hostile_record,))
        hostile_identity = replace(demo_records()[0], source_id=1)
        with self.assertRaisesRegex(ReviewHold, "source-id-invalid"):
            review(request("bounded retry"), (hostile_identity,))

    def test_source_digest_must_be_exact_builtin_lowercase_hex(self) -> None:
        class LyingDigest(str):
            def __ne__(self, other: object) -> bool:
                return False

        original = demo_records()[0]
        hostiles = (
            replace(original, sha256=LyingDigest("forged-digest")),
            replace(original, sha256="A" * 64),
            replace(original, sha256="0" * 63),
        )
        for hostile in hostiles:
            with self.subTest(digest=hostile.sha256), self.assertRaises(ReviewHold):
                review(request("bounded retry"), (hostile,))


if __name__ == "__main__":
    unittest.main()
