#!/usr/bin/env python3
"""Create private AES-CTR experiment contexts with nonce reuse protection.

This tool prepares the manifest used by the PC capture/comparison flow. It does
not provision the FPGA and it never stores the raw key in the nonce registry.
The context JSON itself is private and is created with mode 0600.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import uuid


SCHEMA = 1
KEY_BYTES = 16
NONCE_BYTES = 12
COUNTER_LIMIT = 1 << 32


def _parse_int(value):
    try:
        return int(value, 0)
    except ValueError:
        return int(value, 10)


def _hex_bytes(value, size, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a hexadecimal string")
    try:
        data = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{label} is not hexadecimal") from exc
    if len(data) != size:
        raise ValueError(f"{label} must contain exactly {size} bytes")
    return data


def _validate_length_counter(length, counter):
    if type(length) is not int or length <= 0:
        raise ValueError("bytes must be a positive integer")
    if type(counter) is not int or not 0 <= counter <= 0xffffffff:
        raise ValueError("initial_counter must be an integer in [0, 0xffffffff]")
    blocks = (length + 15) // 16
    if blocks > COUNTER_LIMIT - counter:
        raise ValueError("bytes would wrap the 32-bit counter")


def _timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _private_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    os.chmod(path, 0o600)


@contextmanager
def _registry_lock(path):
    lock_path = Path(f"{path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.chmod(lock_path, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read_registry(path):
    path = Path(path)
    if not path.exists():
        return {"schema": SCHEMA, "contexts": []}
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read nonce registry: {path}") from exc
    if (not isinstance(registry, dict)
            or registry.get("schema") != SCHEMA
            or not isinstance(registry.get("contexts"), list)):
        raise ValueError("unsupported or malformed nonce registry")
    for entry in registry["contexts"]:
        if not isinstance(entry, dict):
            raise ValueError("malformed nonce registry entry")
        _hex_bytes(entry.get("nonce_hex"), NONCE_BYTES, "registry nonce_hex")
        key_id = entry.get("key_sha256")
        if not isinstance(key_id, str) or len(key_id) != 64:
            raise ValueError("malformed registry key fingerprint")
    return registry


def _write_registry(path, registry):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(registry, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def create_context(mode, length, output, registry=None, key_hex=None,
                   nonce_hex=None, initial_counter=0):
    """Create and register one context, returning the public metadata."""
    if mode not in ("baseline", "aes-128-ctr"):
        raise ValueError("mode must be baseline or aes-128-ctr")
    _validate_length_counter(length, initial_counter)
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"context output already exists: {output}")

    context = {
        "schema": SCHEMA,
        "context_id": uuid.uuid4().hex,
        "created_utc": _timestamp(),
        "mode": mode,
        "bytes": length,
    }
    if mode == "baseline":
        if key_hex is not None or nonce_hex is not None:
            raise ValueError("baseline context cannot contain key or nonce")
        _private_json(output, context)
        return context

    if registry is None:
        raise ValueError("secure context requires --registry")
    key = _hex_bytes(key_hex, KEY_BYTES, "key_hex")
    nonce = (secrets.token_bytes(NONCE_BYTES) if nonce_hex is None
             else _hex_bytes(nonce_hex, NONCE_BYTES, "nonce_hex"))
    key_id = hashlib.sha256(key).hexdigest()
    context.update({
        "key_hex": key.hex(),
        "nonce_hex": nonce.hex(),
        "initial_counter": initial_counter,
        "key_sha256": key_id,
    })
    registry = Path(registry)
    with _registry_lock(registry):
        current = _read_registry(registry)
        if any(entry["key_sha256"] == key_id and entry["nonce_hex"] == nonce.hex()
               for entry in current["contexts"]):
            raise ValueError("nonce was already used with this key")
        _private_json(output, context)
        current["contexts"].append({
            "context_id": context["context_id"],
            "created_utc": context["created_utc"],
            "key_sha256": key_id,
            "nonce_hex": nonce.hex(),
            "bytes": length,
            "initial_counter": initial_counter,
            "context_path": str(output),
        })
        try:
            _write_registry(registry, current)
        except Exception:
            output.unlink(missing_ok=True)
            raise
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="create a private experiment context")
    new.add_argument("--mode", choices=("baseline", "aes-128-ctr"), required=True)
    new.add_argument("--bytes", type=int, required=True, dest="length")
    new.add_argument("--output", type=Path, required=True)
    new.add_argument("--registry", type=Path)
    new.add_argument("--key-hex")
    new.add_argument("--nonce-hex")
    new.add_argument("--initial-counter", type=_parse_int, default=0)
    args = parser.parse_args()
    try:
        context = create_context(args.mode, args.length, args.output, args.registry,
                                 args.key_hex, args.nonce_hex, args.initial_counter)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    summary = {key: context[key] for key in
               ("context_id", "created_utc", "mode", "bytes", "nonce_hex")
               if key in context}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
