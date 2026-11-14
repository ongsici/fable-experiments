"""Read the `edits` block from a model reply and build the 600-32-32-6 network.

Re-implementation of the edits language described in the prompt (the original
reader was not released). Usage:
    python parse_edits.py reply.md out.npz
"""
import ast
import json
import re
import sys

import numpy as np

SHAPES = {"W1": (600, 32), "b1": (32,), "W2": (32, 32), "b2": (32,), "W3": (32, 6), "b3": (6,)}
NPZ_KEYS = {
    "W1": "actor/dense1/kernel", "b1": "actor/dense1/bias",
    "W2": "actor/dense2/kernel", "b2": "actor/dense2/bias",
    "W3": "actor/logits/kernel", "b3": "actor/logits/bias",
}
STMT_RE = re.compile(r"^\s*(W1|b1|W2|b2|W3|b3)\s*\[([^\]]*)\]\s*(=|\*=|\+=|-=)\s*(.+)$", re.S)


def last_edits_block(text):
    # Read from the LAST opening fence, so an earlier block left unclosed (reply cut off,
    # then re-sent in full on a later turn) cannot swallow the next block's opening fence.
    m = list(re.finditer(r"```edits[^\n]*\n", text))
    if not m:
        return None, False
    rest = text[m[-1].end():]
    end = rest.find("```")
    if end < 0:  # reply cut off before the closing fence
        return rest, True
    return rest[:end], False


def strip_comment(line):
    return line.split("#", 1)[0].rstrip()


def split_statements(block):
    """Join continuation lines until brackets balance."""
    stmts, buf, depth = [], "", 0
    for raw in block.splitlines():
        line = strip_comment(raw)
        if not line.strip() and depth == 0:
            continue
        buf = (buf + " " + line) if buf else line
        depth = buf.count("[") - buf.count("]")
        if depth <= 0:
            stmts.append(buf.strip())
            buf, depth = "", 0
    if buf.strip():
        stmts.append(buf.strip())
    return stmts


def parse_index(part, dim):
    part = part.strip()
    if ":" not in part:
        i = int(part)
        if not -dim <= i < dim:
            raise IndexError(f"index {i} out of range {dim}")
        return i
    bits = [b.strip() for b in part.split(":")]
    if len(bits) > 3:
        raise ValueError(f"bad slice {part}")
    vals = [int(b) if b else None for b in bits]
    return slice(*vals)


def apply_statement(tensors, stmt):
    m = STMT_RE.match(stmt)
    if not m:
        raise ValueError("unreadable statement")
    name, idx, op, rhs = m.groups()
    t = tensors[name]
    parts = [p for p in idx.split(",")]
    if len(parts) != t.ndim:
        raise ValueError(f"{name} needs {t.ndim} indices")
    key = tuple(parse_index(p, d) for p, d in zip(parts, t.shape))
    value = np.asarray(ast.literal_eval(rhs.strip()), dtype=np.float64)
    if np.any(~np.isfinite(value)) or np.any(np.abs(value) > 1e6):
        raise ValueError("value out of range")
    target_shape = t[key].shape
    if value.ndim > 0 and value.size == int(np.prod(target_shape)) and value.shape != target_shape:
        value = value.reshape(target_shape)
    np.broadcast_to(value, target_shape)  # raises if incompatible
    if op == "=":
        t[key] = value
    elif op == "*=":
        t[key] *= value
    elif op == "+=":
        t[key] += value
    else:
        t[key] -= value
    return int(np.prod(target_shape)) if target_shape else 1


def build(text):
    tensors = {k: np.zeros(s, dtype=np.float64) for k, s in SHAPES.items()}
    block, cut_off = last_edits_block(text)
    report = {"block": block is not None, "cut_off": cut_off, "statements": 0,
              "applied": 0, "entries_written": 0, "errors": []}
    if block is None:
        return tensors, report
    for s in split_statements(block):
        report["statements"] += 1
        try:
            report["entries_written"] += apply_statement(tensors, s)
            report["applied"] += 1
        except Exception as e:  # skipped, as the prompt promises
            report["errors"].append({"statement": s[:200], "error": str(e)})
    report["nonzero"] = {k: int(np.count_nonzero(v)) for k, v in tensors.items()}
    report["nonzero_total"] = sum(report["nonzero"].values())
    report["max_abs"] = {k: float(np.abs(v).max()) for k, v in tensors.items()}
    return tensors, report


def save_npz(tensors, path):
    np.savez(path, **{NPZ_KEYS[k]: v.astype(np.float32) for k, v in tensors.items()})


if __name__ == "__main__":
    reply, out = sys.argv[1], sys.argv[2]
    tensors, report = build(open(reply, encoding="utf-8").read())
    save_npz(tensors, out)
    print(json.dumps(report, indent=1))
