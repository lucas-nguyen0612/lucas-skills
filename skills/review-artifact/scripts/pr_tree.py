#!/usr/bin/env python3
"""Build the file-tree JSON a review artifact renders.

Usage:
  python3 -I pr_tree.py --repo <path> --base <git-ref> [--head <git-ref>] [-o out.json]

--base is what the change is compared against (the PR base, or the merge-base).
--head defaults to HEAD. The output is one JSON object:
  { files, add, del, areas: [{name, files, add, del}], tree: {name, n, add, del, children[], files[]} }
Each file node is {p, a, d, s, full} where s is added | modified | deleted | renamed.
"""

import argparse
import json
import os
import re
import subprocess
import sys


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def parse_status(namestat):
    status, renamed_from = {}, {}
    for line in namestat.splitlines():
        parts = line.split("\t")
        st = parts[0]
        if st.startswith("R") and len(parts) > 2:
            renamed_from[parts[2]] = parts[1]
            status[parts[2]] = "renamed"
        elif st == "A":
            status[parts[1]] = "added"
        elif st == "D":
            status[parts[1]] = "deleted"
        elif len(parts) > 1:
            status[parts[1]] = "modified"
    return status


def resolve_rename(path):
    if "=>" not in path:
        return path
    m = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", path)
    if m:
        pre, _old, new, post = m.groups()
        return pre + new + post
    return path.split(" => ")[-1]


def area_of(path):
    parts = path.split("/")
    if parts[0] in ("apps", "packages") and len(parts) > 1:
        return parts[0] + "/" + parts[1]
    if parts[0] == "supabase" and len(parts) > 1:
        return "supabase/migrations" if parts[1] == "migrations" else "supabase/tests"
    return parts[0]


def compact(node):
    out = {"name": node["name"], "add": 0, "del": 0, "n": 0, "status": {}, "children": [], "files": []}
    for f in node["files"]:
        out["files"].append({"p": os.path.basename(f["path"]), "a": f["add"], "d": f["del"],
                             "s": f["status"], "full": f["path"]})
        out["add"] += f["add"]
        out["del"] += f["del"]
        out["n"] += 1
        out["status"][f["status"]] = out["status"].get(f["status"], 0) + 1
    for key in sorted(node["children"]):
        child = compact(node["children"][key])
        out["children"].append(child)
        out["add"] += child["add"]
        out["del"] += child["del"]
        out["n"] += child["n"]
        for s, v in child["status"].items():
            out["status"][s] = out["status"].get(s, 0) + v
    out["children"].sort(key=lambda c: -c["n"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("-o", "--out", default="pr-tree.json")
    a = ap.parse_args()

    status = parse_status(git(a.repo, "diff", "--name-status", "-M", a.base, a.head))
    files = []
    for line in git(a.repo, "diff", "--numstat", "-M", a.base, a.head).splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add, dele, path = parts[0], parts[1], parts[2]
        path = resolve_rename(path)
        files.append({
            "path": path,
            "add": 0 if add == "-" else int(add),
            "del": 0 if dele == "-" else int(dele),
            "status": status.get(path, "modified"),
        })

    areas = {}
    for f in files:
        bucket = areas.setdefault(area_of(f["path"]), {"files": 0, "add": 0, "del": 0})
        bucket["files"] += 1
        bucket["add"] += f["add"]
        bucket["del"] += f["del"]

    root = {"name": os.path.basename(os.path.abspath(a.repo)), "children": {}, "files": []}
    for f in files:
        node = root
        for seg in f["path"].split("/")[:-1]:
            node = node["children"].setdefault(seg, {"name": seg, "children": {}, "files": []})
        node["files"].append(f)

    payload = {
        "files": len(files),
        "add": sum(f["add"] for f in files),
        "del": sum(f["del"] for f in files),
        "areas": [{"name": k, **v} for k, v in sorted(areas.items(), key=lambda kv: -kv[1]["files"])],
        "tree": compact(root),
    }
    with open(a.out, "w") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print(f"{payload['files']} files, +{payload['add']} -{payload['del']} -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
