"""Definition identity for Path B v2.1 (frozen with PROTOCOL.md, Section 8).

  python3 definition_hash.py ros1 <pkg/Type> <search_dir> [<search_dir> ...]
      ROS 1 message md5sum by the genmsg algorithm: comments and blank lines removed,
      constants first as "type NAME=value", then fields as "type name"; a nested
      message type is replaced by its own md5sum (array brackets dropped for nested
      types, kept for built-in types); md5 of the lines joined by newline.
      <search_dir> holds <pkg>/msg/<Type>.msg trees (the snapshot and any
      dependency definition directories). Verified against seven published
      md5sums (std_msgs/String, std_msgs/Header, geometry_msgs/Pose, PoseStamped,
      PoseArray, sensor_msgs/NavSatStatus, NavSatFix) on 2026-09-25.
  python3 definition_hash.py sha256 <file>
      SHA-256 of the definition text with comments, trailing whitespace and blank
      lines removed. A proxy for ROS 2 type hashes; labelled as such in results.

Output: one JSON object {"algorithm": ..., "kind": ..., "value": ...}.
"""
import hashlib
import json
import os
import re
import sys

BUILTIN = {"bool", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64",
           "float32", "float64", "string", "time", "duration", "char", "byte"}
_CONST = re.compile(r"^(\w+)\s+(\w+)\s*=\s*(.+)$")
_FIELD = re.compile(r"^([\w/]+)(\[\d*\])?\s+(\w+)$")


def clean_lines(text):
    out = []
    for raw in text.splitlines():
        stripped = raw.strip()
        is_string_const = stripped.startswith("string ") and "=" in stripped
        line = stripped if is_string_const else raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _package_name(msg_path):
    """Name from the nearest package.xml above a msg file (snapshot dirs are opaque ids)."""
    d = os.path.dirname(os.path.dirname(msg_path))
    for _ in range(6):
        px = os.path.join(d, "package.xml")
        if os.path.exists(px):
            m = re.search(r"<name>\s*([\w-]+)\s*</name>", open(px, errors="replace").read())
            return m.group(1) if m else None
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return os.path.basename(d)


def find_msg(pkg, name, dirs):
    for d in dirs:
        for root, _, files in os.walk(d):
            if os.path.basename(root) == "msg" and name + ".msg" in files:
                cand = os.path.join(root, name + ".msg")
                if _package_name(cand) == pkg:
                    return cand
    raise FileNotFoundError(f"{pkg}/{name}.msg not found under {dirs}")


def ros1_md5(pkg, name, dirs):
    text = open(find_msg(pkg, name, dirs)).read()
    consts, fields = [], []
    for line in clean_lines(text):
        m = _CONST.match(line)
        if m and m.group(1) in BUILTIN:
            t, cname, val = m.groups()
            if t == "string":
                val = line.split("=", 1)[1].strip()
            consts.append(f"{t} {cname}={val.strip()}")
            continue
        m = _FIELD.match(line)
        if not m:
            raise ValueError(f"cannot parse line {line!r} in {pkg}/{name}")
        base, arr, fname = m.group(1), m.group(2) or "", m.group(3)
        if base in BUILTIN:
            fields.append(f"{base}{arr} {fname}")
        else:
            if base == "Header":
                p, t = "std_msgs", "Header"
            elif "/" in base:
                p, t = base.split("/", 1)
            else:
                p, t = pkg, base
            fields.append(f"{ros1_md5(p, t, dirs)} {fname}")  # genmsg drops the brackets for nested types
    return hashlib.md5("\n".join(consts + fields).encode()).hexdigest()


def sha256_normalised(path):
    lines = [l.split("#", 1)[0].rstrip() for l in open(path).read().splitlines()]
    return hashlib.sha256("\n".join(l for l in lines if l.strip()).encode()).hexdigest()


def main():
    if sys.argv[1] == "ros1":
        pkg, name = sys.argv[2].split("/")
        print(json.dumps({"algorithm": "ros1_md5", "kind": "msg", "value": ros1_md5(pkg, name, sys.argv[3:])}))
    elif sys.argv[1] == "sha256":
        kind = os.path.splitext(sys.argv[2])[1].lstrip(".") or "text"
        print(json.dumps({"algorithm": "sha256_normalised", "kind": kind, "value": sha256_normalised(sys.argv[2])}))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
