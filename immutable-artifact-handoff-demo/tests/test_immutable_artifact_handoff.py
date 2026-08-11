from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path
from unittest import mock

from immutable_artifact_handoff import ARTIFACT_NAME, load_handoff, publish


class ImmutableArtifactHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "root"
        self.root.mkdir()
        self.artifact = b'{"synthetic":"artifact"}'
        self.generation = hashlib.sha256(self.artifact).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _published(self) -> Path:
        result = publish(self.root, self.artifact)
        self.assertEqual((result.status, result.reason), ("published", "receipt-last-published"))
        return self.root / "bundles" / self.generation

    def test_receipt_last_metadata_only_review_handoff(self) -> None:
        self._published()
        result = load_handoff(self.root, self.generation)
        self.assertEqual((result.status, result.reason), ("ready", "review-required"))
        self.assertEqual(result.handoff["review_status"], "review-required")
        self.assertEqual(result.handoff["authority"], {"network": False, "provider": False, "model": False, "deployment": False, "external_effect": False})
        self.assertNotIn("artifact", result.handoff)

    def test_missing_receipt_and_partial_publication_hold(self) -> None:
        bundle = self.root / "bundles" / self.generation
        bundle.mkdir(parents=True)
        (self.root / "receipts").mkdir()
        (bundle / ARTIFACT_NAME).write_bytes(self.artifact)
        (bundle / "manifest.json").write_bytes(b"{}")
        self.assertEqual(load_handoff(self.root, self.generation).reason, "receipt-missing")
        self.assertEqual(publish(self.root, self.artifact).reason, "conflicting-or-partial-existing-publication")
        self.assertFalse((self.root / "receipts" / f"{self.generation}.receipt.json").exists())

    def test_digest_conflict_holds(self) -> None:
        bundle = self._published()
        (bundle / ARTIFACT_NAME).write_bytes(b'{"synthetic":"changed"}')
        self.assertEqual(load_handoff(self.root, self.generation).reason, "artifact-digest-conflict")

    def test_symlink_root_ancestor_and_leaf_hold(self) -> None:
        real = Path(self.temporary.name) / "real"
        real.mkdir()
        self.assertEqual(publish(real, self.artifact).status, "published")
        root_link = Path(self.temporary.name) / "root-link"
        root_link.symlink_to(real, target_is_directory=True)
        self.assertEqual(load_handoff(root_link, self.generation).reason, "root-ancestor-invalid")
        ancestor = Path(self.temporary.name) / "ancestor"
        ancestor.symlink_to(real, target_is_directory=True)
        self.assertEqual(load_handoff(ancestor / "child", self.generation).reason, "root-ancestor-invalid")
        receipt = real / "receipts" / f"{self.generation}.receipt.json"
        receipt.unlink()
        receipt.symlink_to(real / "bundles" / self.generation / "manifest.json")
        self.assertEqual(load_handoff(real, self.generation).reason, "receipt-leaf-invalid")

    def test_root_replaced_after_read_holds(self) -> None:
        self._published()
        def replace_root(stage: str) -> None:
            if stage == "receipt":
                moved = self.root.with_name("root-old")
                self.root.rename(moved)
                self.root.mkdir()
        result = load_handoff(self.root, self.generation, _after_read=replace_root)
        self.assertEqual(result.status, "held")
        self.assertIn(result.reason, {"bundles-directory-invalid", "root-or-ancestor-replaced"})

    def test_root_replaced_after_first_bundle_read_holds(self) -> None:
        self._published()
        def replace_root(stage: str) -> None:
            if stage == "artifact":
                moved = self.root.with_name("root-after-artifact")
                self.root.rename(moved)
                self.root.mkdir()
        result = load_handoff(self.root, self.generation, _after_read=replace_root)
        self.assertEqual(result.status, "held")

    def test_leaf_replaced_after_read_holds(self) -> None:
        bundle = self._published()
        def replace_leaf(stage: str) -> None:
            if stage == "artifact":
                artifact = bundle / ARTIFACT_NAME
                artifact.rename(bundle / "old-artifact")
                artifact.write_bytes(self.artifact)
        result = load_handoff(self.root, self.generation, _after_read=replace_leaf)
        self.assertEqual((result.status, result.reason), ("held", "artifact-leaf-replaced"))

    def test_same_byte_receipt_replaced_after_read_holds(self) -> None:
        self._published()
        receipt = self.root / "receipts" / f"{self.generation}.receipt.json"
        def replace_receipt(stage: str) -> None:
            if stage == "artifact":
                original = receipt.read_bytes()
                receipt.rename(receipt.with_suffix(".old"))
                receipt.write_bytes(original)
        result = load_handoff(self.root, self.generation, _after_read=replace_receipt)
        self.assertEqual((result.status, result.reason), ("held", "receipt-leaf-replaced"))

    def test_bundle_parent_replaced_after_read_holds(self) -> None:
        bundle = self._published()
        def replace_bundle(stage: str) -> None:
            if stage == "artifact":
                bundle.rename(bundle.with_name(f"{self.generation}-old"))
                bundle.mkdir()
        result = load_handoff(self.root, self.generation, _after_read=replace_bundle)
        self.assertEqual(result.status, "held")
        self.assertIn(result.reason, {"artifact-leaf-replaced", "manifest-leaf-replaced", "bundle-directory-replaced"})

    def test_terminal_rewalk_rejects_same_byte_bundle_clone_after_root_check(self) -> None:
        bundle = self._published()
        def replace_bundle(stage: str) -> None:
            if stage == "terminal-root-checked":
                original = bundle.with_name(f"{self.generation}-terminal-old")
                bundle.rename(original)
                shutil.copytree(original, bundle)
        result = load_handoff(self.root, self.generation, _after_read=replace_bundle)
        self.assertEqual(result.status, "held")
        self.assertIn(result.reason, {"artifact-leaf-replaced", "manifest-leaf-replaced", "bundle-directory-replaced"})

    def test_in_place_leaf_mutation_after_read_holds(self) -> None:
        bundle = self._published()
        def mutate_artifact(stage: str) -> None:
            if stage == "artifact":
                with (bundle / ARTIFACT_NAME).open("r+b") as stream:
                    stream.write(b"X")
                    stream.flush()
                    os.fsync(stream.fileno())
        result = load_handoff(self.root, self.generation, _after_read=mutate_artifact)
        self.assertEqual((result.status, result.reason), ("held", "artifact-leaf-mutated"))

    def test_exact_replay_is_idempotent(self) -> None:
        self._published()
        replay = publish(self.root, self.artifact)
        self.assertEqual((replay.status, replay.reason), ("replayed", "exact-replay"))
        self.assertEqual(replay.handoff["generation"], self.generation)

    def test_conflicting_existing_leaf_holds_without_overwrite(self) -> None:
        bundle = self.root / "bundles" / self.generation
        bundle.mkdir(parents=True)
        conflict = b'{"synthetic":"conflict"}'
        (bundle / ARTIFACT_NAME).write_bytes(conflict)
        original = (bundle / ARTIFACT_NAME).read_bytes()
        result = publish(self.root, self.artifact)
        self.assertEqual(result.reason, "conflicting-or-partial-existing-publication")
        self.assertEqual((bundle / ARTIFACT_NAME).read_bytes(), original)

    def test_strict_duplicate_missing_extra_and_reordered_receipts_hold(self) -> None:
        self._published()
        receipt = self.root / "receipts" / f"{self.generation}.receipt.json"
        receipt.write_bytes(b'{"schema":"immutable-artifact-receipt-v1","schema":"immutable-artifact-receipt-v1"}')
        self.assertEqual(load_handoff(self.root, self.generation).reason, "receipt-json-invalid")
        for mutation, expected in (
            (lambda value: {key: item for key, item in value.items() if key != "bundle"}, "receipt-keyset-invalid"),
            (lambda value: {**value, "unexpected": True}, "receipt-keyset-invalid"),
        ):
            root = Path(tempfile.mkdtemp(dir=self.temporary.name))
            published = publish(root, self.artifact)
            self.assertEqual(published.status, "published")
            path = root / "receipts" / f"{self.generation}.receipt.json"
            value = json.loads(path.read_text())
            path.write_bytes(json.dumps(mutation(value), sort_keys=True, separators=(",", ":")).encode())
            self.assertEqual(load_handoff(root, self.generation).reason, expected)
        root = Path(tempfile.mkdtemp(dir=self.temporary.name))
        self.assertEqual(publish(root, self.artifact).status, "published")
        path = root / "receipts" / f"{self.generation}.receipt.json"
        value = json.loads(path.read_text())
        path.write_bytes(json.dumps(dict(reversed(list(value.items()))), separators=(",", ":")).encode())
        self.assertEqual(load_handoff(root, self.generation).reason, "receipt-canonical-invalid")

    def test_missing_and_extra_bundle_members_hold(self) -> None:
        bundle = self._published()
        (bundle / "manifest.json").unlink()
        self.assertEqual(load_handoff(self.root, self.generation).reason, "bundle-name-set-conflict")
        other = Path(tempfile.mkdtemp(dir=self.temporary.name))
        self.assertEqual(publish(other, self.artifact).status, "published")
        (other / "bundles" / self.generation / "unexpected.json").write_text("synthetic")
        self.assertEqual(load_handoff(other, self.generation).reason, "bundle-name-set-conflict")

    def test_concurrent_publishers_leave_one_verifiable_receipt(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: publish(self.root, self.artifact), range(2)))
        self.assertEqual(sum(result.status == "published" for result in results), 1)
        self.assertTrue(all(result.status in {"published", "replayed", "held"} for result in results))
        self.assertEqual(load_handoff(self.root, self.generation).status, "ready")

    def test_invalid_source_never_creates_a_receipt(self) -> None:
        for invalid in (b"", b"x" * (128 * 1024 + 1)):
            result = publish(self.root, invalid)
            self.assertEqual((result.status, result.reason), ("held", "artifact-input-invalid"))
            self.assertFalse((self.root / "receipts").exists())

    def test_short_reads_are_completed_before_validation(self) -> None:
        self._published()
        actual_read = os.read
        def short_read(fd: int, amount: int) -> bytes:
            return actual_read(fd, max(1, amount // 7))
        with mock.patch("immutable_artifact_handoff.os.read", side_effect=short_read):
            self.assertEqual(load_handoff(self.root, self.generation).status, "ready")


if __name__ == "__main__":
    unittest.main()
