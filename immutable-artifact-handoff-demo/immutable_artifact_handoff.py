"""A local, standard-library-only immutable artifact handoff demonstration.

The publisher writes an artifact and a canonical manifest before creating a
receipt.  The receipt is the sole completion marker.  The loader accepts only
one descriptor-pinned, fully re-attested receipt/bundle family and returns a
metadata-only, review-required handoff.  It performs no network, provider,
model, deployment, or external-effect action.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


AUTHORITY = {
    "network": False,
    "provider": False,
    "model": False,
    "deployment": False,
    "external_effect": False,
}
MANIFEST_SCHEMA = "immutable-artifact-manifest-v1"
RECEIPT_SCHEMA = "immutable-artifact-receipt-v1"
HANDOFF_SCHEMA = "immutable-artifact-review-handoff-v1"
ARTIFACT_NAME = "artifact.json"
MAX_BYTES = 128 * 1024
_TOKEN_FIELDS = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _token(info: os.stat_result) -> tuple[int, ...]:
    return tuple(int(getattr(info, field)) for field in _TOKEN_FIELDS)


def _name(value: str, reason: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise _Held(reason)
    return value


class _Held(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    handoff: Mapping[str, Any] | None = None


@dataclass
class _HeldFile:
    parent: "_HeldDir"
    name: str
    fd: int
    token: tuple[int, ...]
    data: bytes

    def reattest(self, label: str) -> None:
        try:
            before = os.fstat(self.fd)
            os.lseek(self.fd, 0, os.SEEK_SET)
            reread = bytearray()
            while True:
                part = os.read(self.fd, 65536)
                if not part:
                    break
                reread.extend(part)
                if len(reread) > MAX_BYTES:
                    raise _Held(f"{label}-leaf-mutated")
            after = os.fstat(self.fd)
            current = os.stat(self.name, dir_fd=self.parent.fd, follow_symlinks=False)
            held = os.fstat(self.fd)
        except OSError as error:
            raise _Held(f"{label}-leaf-replaced") from error
        if bytes(reread) != self.data:
            raise _Held(f"{label}-leaf-mutated")
        if (
            not stat.S_ISREG(current.st_mode)
            or _token(before) != self.token
            or _token(after) != self.token
            or _token(current) != self.token
            or _token(held) != self.token
        ):
            raise _Held(f"{label}-leaf-replaced")

    def close(self) -> None:
        os.close(self.fd)


@dataclass
class _HeldDir:
    path: Path
    fd: int
    token: tuple[int, ...]
    root: "_HeldRoot"
    parent: "_HeldDir | None" = None
    name: str | None = None

    def child_dir(self, name: str, label: str) -> "_HeldDir":
        _name(name, f"{label}-name-invalid")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            info = os.fstat(fd)
        except OSError as error:
            raise _Held(f"{label}-directory-invalid") from error
        if not stat.S_ISDIR(info.st_mode):
            os.close(fd)
            raise _Held(f"{label}-directory-invalid")
        return _HeldDir(self.path / name, fd, _token(info), self.root, self, name)

    def read_file(self, name: str, label: str) -> _HeldFile:
        _name(name, f"{label}-name-invalid")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                os.close(fd)
                raise _Held(f"{label}-leaf-invalid")
            data = bytearray()
            while True:
                part = os.read(fd, 65536)
                if not part:
                    break
                data.extend(part)
                if len(data) > MAX_BYTES:
                    os.close(fd)
                    raise _Held(f"{label}-leaf-invalid")
            after = os.fstat(fd)
            current = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError as error:
            raise _Held(f"{label}-missing") from error
        except _Held:
            raise
        except OSError as error:
            raise _Held(f"{label}-leaf-invalid") from error
        if _token(before) != _token(after) or _token(before) != _token(current):
            os.close(fd)
            raise _Held(f"{label}-leaf-replaced")
        return _HeldFile(self, name, fd, _token(before), bytes(data))

    def exact_names(self, expected: set[str], label: str) -> None:
        try:
            names = set(os.listdir(self.fd))
        except OSError as error:
            raise _Held(f"{label}-directory-invalid") from error
        if names != expected:
            raise _Held(f"{label}-name-set-conflict")

    def reattest(self, label: str) -> None:
        try:
            held = os.fstat(self.fd)
            if self.parent is None or self.name is None:
                current = os.stat(self.path, follow_symlinks=False)
            else:
                current = os.stat(self.name, dir_fd=self.parent.fd, follow_symlinks=False)
        except OSError as error:
            raise _Held(f"{label}-directory-replaced") from error
        if not stat.S_ISDIR(current.st_mode) or _token(held) != self.token or _token(current) != self.token:
            raise _Held(f"{label}-directory-replaced")

    def close(self) -> None:
        os.close(self.fd)


@dataclass
class _HeldRoot:
    path: Path
    components: tuple[tuple[str, tuple[int, ...]], ...]
    fd: int
    token: tuple[int, ...]

    @classmethod
    def open(cls, path: Path) -> "_HeldRoot":
        absolute = path.expanduser().absolute()
        if not absolute.is_absolute():  # defensive; absolute() above should guarantee this.
            raise _Held("root-path-invalid")
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        components: list[tuple[str, tuple[int, ...]]] = []
        try:
            for part in absolute.parts[1:]:
                try:
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    info = os.fstat(next_fd)
                except OSError as error:
                    raise _Held("root-ancestor-invalid") from error
                if not stat.S_ISDIR(info.st_mode):
                    os.close(next_fd)
                    raise _Held("root-ancestor-invalid")
                os.close(fd)
                fd = next_fd
                components.append((part, _token(info)))
        except Exception:
            os.close(fd)
            raise
        return cls(absolute, tuple(components), fd, _token(os.fstat(fd)))

    def as_dir(self) -> _HeldDir:
        return _HeldDir(self.path, self.fd, self.token, self)

    def reattest_chain(self) -> None:
        fresh = _HeldRoot.open(self.path)
        try:
            if fresh.components != self.components or fresh.token != self.token:
                raise _Held("root-or-ancestor-replaced")
        finally:
            fresh.close()

    def close(self) -> None:
        os.close(self.fd)


def _decode_canonical(raw: bytes, schema: str, label: str) -> Mapping[str, Any]:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise _Held(f"{label}-json-invalid") from error
    if not isinstance(value, dict) or value.get("schema") != schema or _canonical(value) != raw:
        raise _Held(f"{label}-canonical-invalid")
    return value


def _hex(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise _Held(f"{label}-invalid")
    return value


def _manifest(generation: str, artifact: bytes) -> Mapping[str, Any]:
    return {
        "artifact": {"name": ARTIFACT_NAME, "sha256": _sha256(artifact), "size": len(artifact)},
        "authority": AUTHORITY,
        "generation": generation,
        "schema": MANIFEST_SCHEMA,
    }


def _receipt(generation: str, manifest_bytes: bytes, artifact_sha256: str) -> Mapping[str, Any]:
    return {
        "artifact_sha256": artifact_sha256,
        "authority": AUTHORITY,
        "bundle": f"bundles/{generation}",
        "generation": generation,
        "manifest_sha256": _sha256(manifest_bytes),
        "schema": RECEIPT_SCHEMA,
    }


def _write_new(parent: _HeldDir, name: str, data: bytes, label: str) -> None:
    _name(name, f"{label}-name-invalid")
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent.fd)
    except FileExistsError as error:
        raise _Held(f"{label}-already-exists") from error
    except OSError as error:
        raise _Held(f"{label}-write-failed") from error
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise _Held(f"{label}-write-failed")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


def _mkdir(parent: _HeldDir, name: str, label: str) -> _HeldDir:
    _name(name, f"{label}-name-invalid")
    try:
        os.mkdir(name, 0o700, dir_fd=parent.fd)
        os.fsync(parent.fd)
    except FileExistsError as error:
        raise _Held(f"{label}-already-exists") from error
    except OSError as error:
        raise _Held(f"{label}-create-failed") from error
    return parent.child_dir(name, label)


def _ensure_dir(parent: _HeldDir, name: str, label: str) -> _HeldDir:
    try:
        return parent.child_dir(name, label)
    except _Held as error:
        if error.reason != f"{label}-directory-invalid":
            raise
    try:
        return _mkdir(parent, name, label)
    except _Held as error:
        if error.reason != f"{label}-already-exists":
            raise
    return parent.child_dir(name, label)


def _terminal_rewalk(
    root: _HeldRoot,
    generation: str,
    receipt_file: _HeldFile,
    receipts: _HeldDir,
    manifest_file: _HeldFile,
    artifact_file: _HeldFile,
    bundles: _HeldDir,
    bundle: _HeldDir,
    handoff: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Make the final return contingent on a fresh, exact descriptor rewalk.

    This second walk is deliberately after the first held-family validation.
    It catches a same-byte new-inode descendant replacement between that first
    validation and the root-chain re-attestation; no non-cleanup work follows
    its own leaf byte/token checks.
    """
    fresh_root = _HeldRoot.open(root.path)
    fresh_files: list[_HeldFile] = []
    fresh_dirs: list[_HeldDir] = []
    try:
        if fresh_root.components != root.components or fresh_root.token != root.token:
            raise _Held("root-or-ancestor-replaced")
        fresh_dir = fresh_root.as_dir()
        fresh_receipts = fresh_dir.child_dir("receipts", "receipts")
        fresh_dirs.append(fresh_receipts)
        fresh_receipt = fresh_receipts.read_file(f"{generation}.receipt.json", "receipt")
        fresh_files.append(fresh_receipt)
        fresh_bundles = fresh_dir.child_dir("bundles", "bundles")
        fresh_dirs.append(fresh_bundles)
        fresh_bundle = fresh_bundles.child_dir(generation, "bundle")
        fresh_dirs.append(fresh_bundle)
        fresh_bundle.exact_names({ARTIFACT_NAME, "manifest.json"}, "bundle")
        fresh_manifest = fresh_bundle.read_file("manifest.json", "manifest")
        fresh_files.append(fresh_manifest)
        fresh_artifact = fresh_bundle.read_file(ARTIFACT_NAME, "artifact")
        fresh_files.append(fresh_artifact)

        for prior, current, label in (
            (receipt_file, fresh_receipt, "receipt"),
            (manifest_file, fresh_manifest, "manifest"),
            (artifact_file, fresh_artifact, "artifact"),
        ):
            if prior.token != current.token or prior.data != current.data:
                raise _Held(f"{label}-leaf-replaced")
        for prior, current, label in (
            (receipts, fresh_receipts, "receipts"),
            (bundles, fresh_bundles, "bundles"),
            (bundle, fresh_bundle, "bundle"),
        ):
            if prior.token != current.token:
                raise _Held(f"{label}-directory-replaced")

        # The final mutable reads: newly held leaves are rehashed/read back and
        # then this function immediately returns the already validated handoff.
        for held_file, label in ((fresh_artifact, "artifact"), (fresh_manifest, "manifest"), (fresh_receipt, "receipt")):
            held_file.reattest(label)
        return handoff
    finally:
        for held_file in reversed(fresh_files):
            held_file.close()
        for held_dir in reversed(fresh_dirs):
            held_dir.close()
        fresh_root.close()


def _load(root_path: Path, generation: str, after_read: Callable[[str], None] | None = None) -> Mapping[str, Any]:
    generation = _hex(generation, "generation")
    root = _HeldRoot.open(root_path)
    held_files: list[_HeldFile] = []
    held_dirs: list[tuple[_HeldDir, str]] = []
    try:
        root_dir = root.as_dir()
        receipts = root_dir.child_dir("receipts", "receipts")
        held_dirs.append((receipts, "receipts"))
        receipt_file = receipts.read_file(f"{generation}.receipt.json", "receipt")
        held_files.append(receipt_file)
        receipt = _decode_canonical(receipt_file.data, RECEIPT_SCHEMA, "receipt")
        if after_read is not None:
            after_read("receipt")
        if set(receipt) != {"artifact_sha256", "authority", "bundle", "generation", "manifest_sha256", "schema"}:
            raise _Held("receipt-keyset-invalid")
        if receipt["authority"] != AUTHORITY or receipt["generation"] != generation or receipt["bundle"] != f"bundles/{generation}":
            raise _Held("receipt-binding-invalid")
        artifact_hash = _hex(receipt["artifact_sha256"], "receipt-artifact-sha256")
        manifest_hash = _hex(receipt["manifest_sha256"], "receipt-manifest-sha256")

        bundles = root_dir.child_dir("bundles", "bundles")
        held_dirs.append((bundles, "bundles"))
        bundle = bundles.child_dir(generation, "bundle")
        held_dirs.append((bundle, "bundle"))
        bundle.exact_names({ARTIFACT_NAME, "manifest.json"}, "bundle")
        manifest_file = bundle.read_file("manifest.json", "manifest")
        held_files.append(manifest_file)
        manifest = _decode_canonical(manifest_file.data, MANIFEST_SCHEMA, "manifest")
        artifact_file = bundle.read_file(ARTIFACT_NAME, "artifact")
        held_files.append(artifact_file)
        if after_read is not None:
            after_read("artifact")
        if _sha256(manifest_file.data) != manifest_hash:
            raise _Held("receipt-manifest-digest-conflict")
        if set(manifest) != {"artifact", "authority", "generation", "schema"} or manifest["authority"] != AUTHORITY or manifest["generation"] != generation:
            raise _Held("manifest-binding-invalid")
        artifact = manifest["artifact"]
        if not isinstance(artifact, dict) or set(artifact) != {"name", "sha256", "size"} or artifact.get("name") != ARTIFACT_NAME:
            raise _Held("manifest-artifact-invalid")
        if _sha256(artifact_file.data) != artifact_hash:
            raise _Held("artifact-digest-conflict")
        if artifact.get("size") != len(artifact_file.data) or _hex(artifact.get("sha256"), "manifest-artifact-sha256") != artifact_hash:
            raise _Held("manifest-artifact-digest-conflict")

        # Final mutable work is leaf-to-root.  Nothing occurs after the root chain check.
        for held_file, label in ((artifact_file, "artifact"), (manifest_file, "manifest"), (receipt_file, "receipt")):
            held_file.reattest(label)
        for held_dir, label in reversed(held_dirs):
            held_dir.reattest(label)
        root.reattest_chain()
        if after_read is not None:
            after_read("terminal-root-checked")
        handoff = {
            "schema": HANDOFF_SCHEMA,
            "generation": generation,
            "artifact_sha256": artifact_hash,
            "manifest_sha256": manifest_hash,
            "review_status": "review-required",
            "authority": AUTHORITY,
        }
        return _terminal_rewalk(root, generation, receipt_file, receipts, manifest_file, artifact_file, bundles, bundle, handoff)
    finally:
        for held_file in reversed(held_files):
            held_file.close()
        for held_dir, _ in reversed(held_dirs):
            held_dir.close()
        root.close()


def load_handoff(root: Path, generation: str, *, _after_read: Callable[[str], None] | None = None) -> Result:
    """Load one completed publication as metadata-only, review-required work."""
    try:
        return Result("ready", "review-required", _load(root, generation, _after_read))
    except _Held as error:
        return Result("held", error.reason)


def publish(root: Path, artifact: bytes) -> Result:
    """Create an immutable synthetic publication or return a named fail-closed hold."""
    if not isinstance(artifact, bytes) or not artifact or len(artifact) > MAX_BYTES:
        return Result("held", "artifact-input-invalid")
    generation = _sha256(artifact)
    manifest_bytes = _canonical(_manifest(generation, artifact))
    receipt_bytes = _canonical(_receipt(generation, manifest_bytes, generation))
    root_hold: _HeldRoot | None = None
    extra_dirs: list[_HeldDir] = []
    try:
        root_hold = _HeldRoot.open(root)
        root_dir = root_hold.as_dir()
        bundles = _ensure_dir(root_dir, "bundles", "bundles")
        receipts = _ensure_dir(root_dir, "receipts", "receipts")
        extra_dirs.extend((bundles, receipts))
        try:
            bundle = _mkdir(bundles, generation, "bundle")
        except _Held as error:
            if error.reason != "bundle-already-exists":
                raise
            loaded = load_handoff(root, generation)
            if loaded.status == "ready":
                return Result("replayed", "exact-replay", loaded.handoff)
            return Result("held", "conflicting-or-partial-existing-publication")
        extra_dirs.append(bundle)
        _write_new(bundle, ARTIFACT_NAME, artifact, "artifact")
        _write_new(bundle, "manifest.json", manifest_bytes, "manifest")
        os.fsync(bundle.fd)
        try:
            _write_new(receipts, f"{generation}.receipt.json", receipt_bytes, "receipt")
        except _Held as error:
            if error.reason != "receipt-already-exists":
                raise
            loaded = load_handoff(root, generation)
            if loaded.status == "ready":
                return Result("replayed", "exact-replay", loaded.handoff)
            return Result("held", "conflicting-existing-receipt")
        os.fsync(receipts.fd)
        # Publication necessarily changed this root's directory generation.  The
        # fresh loader below acquires a new held root and performs the terminal
        # leaf-to-root re-attestation without any further publication mutation.
        loaded = load_handoff(root, generation)
        if loaded.status != "ready":
            return Result("held", f"publication-verification-{loaded.reason}")
        return Result("published", "receipt-last-published", loaded.handoff)
    except _Held as error:
        return Result("held", error.reason)
    finally:
        for directory in reversed(extra_dirs):
            directory.close()
        if root_hold is not None:
            root_hold.close()
