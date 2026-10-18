"""
measure_diff.py - Markdown diff of the semantic model between two git refs.

Compares the TMDL measures (_Measures.tmdl) and relationships.tmdl, so a pull request
shows exactly which business definitions changed. Used by the `model-diff` CI job.

Usage: python tools/measure_diff.py <base-ref> <head-ref>   (prints Markdown)
"""
import re
import subprocess
import sys

MODEL = "powerbi/Olist Delivery Experience/Olist Delivery Experience.SemanticModel/definition"
MEASURES = f"{MODEL}/tables/_Measures.tmdl"
RELATIONSHIPS = f"{MODEL}/relationships.tmdl"
NL = "\n"


def show(ref: str, path: str) -> str:
    try:
        return subprocess.run(["git", "show", f"{ref}:{path}"], check=True, capture_output=True,
                              text=True, encoding="utf-8").stdout
    except subprocess.CalledProcessError:
        return ""


def parse_measures(text: str) -> dict:
    """name -> {expr, formatString, displayFolder}"""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^\tmeasure (?:'([^']+)'|(\S+)) =\s*(.*)$", line)
        if m:
            cur = m.group(1) or m.group(2)
            first = m.group(3).strip()
            out[cur] = {"expr": [first] if first else [], "formatString": "", "displayFolder": ""}
            continue
        if cur is None:
            continue
        if line.startswith("\t\t\t"):
            out[cur]["expr"].append(line.strip())
        elif line.startswith("\t\tformatString: "):
            out[cur]["formatString"] = line.split(": ", 1)[1]
        elif line.startswith("\t\tdisplayFolder: "):
            out[cur]["displayFolder"] = line.split(": ", 1)[1]
        elif line.startswith("\tcolumn ") or line.startswith("\tpartition "):
            cur = None
    for v in out.values():
        v["expr"] = NL.join(v["expr"])
    return out


def parse_relationships(text: str) -> set:
    rels, frm = set(), None
    for line in text.splitlines():
        if line.startswith("\tfromColumn: "):
            frm = line.split(": ", 1)[1]
        elif line.startswith("\ttoColumn: "):
            rels.add(f"{frm} -> {line.split(': ', 1)[1]}")
    return rels


def code(expr: str, prefix: str = "") -> str:
    return NL.join(prefix + ln for ln in expr.split(NL))


def main(base: str, head: str) -> None:
    mb, mh = parse_measures(show(base, MEASURES)), parse_measures(show(head, MEASURES))
    rb, rh = parse_relationships(show(base, RELATIONSHIPS)), parse_relationships(show(head, RELATIONSHIPS))
    added = sorted(set(mh) - set(mb))
    removed = sorted(set(mb) - set(mh))
    changed = sorted(n for n in set(mb) & set(mh) if mb[n] != mh[n])
    print("### Semantic model diff" + NL)
    print(f"Measures: **{len(mh)}** (base {len(mb)}) - added {len(added)}, removed {len(removed)}, changed {len(changed)}  ")
    print(f"Relationships: **{len(rh)}** (base {len(rb)}) - added {len(rh - rb)}, removed {len(rb - rh)}" + NL)
    if not (added or removed or changed or rh != rb):
        print("No change to measures or relationships.")
        return
    for title, names, src in (("Added", added, mh), ("Removed", removed, mb)):
        if names:
            print(f"<details><summary><b>{title} measures ({len(names)})</b></summary>" + NL)
            for n in names:
                print(f"- `{n}` ({src[n]['displayFolder'] or 'no folder'}; format `{src[n]['formatString'] or '-'}`)")
                print("  ```dax" + NL + code(src[n]["expr"], "  ") + NL + "  ```")
            print("</details>" + NL)
    if changed:
        print(f"<details open><summary><b>Changed measures ({len(changed)})</b></summary>" + NL)
        for n in changed:
            print(f"**`{n}`**" + NL)
            if mb[n]["expr"] != mh[n]["expr"]:
                print("```diff" + NL + code(mb[n]["expr"], "- ") + NL + code(mh[n]["expr"], "+ ") + NL + "```")
            for k in ("formatString", "displayFolder"):
                if mb[n][k] != mh[n][k]:
                    print(f"- {k}: `{mb[n][k] or '-'}` -> `{mh[n][k] or '-'}`")
            print()
        print("</details>" + NL)
    for title, rels in (("Added relationships", rh - rb), ("Removed relationships", rb - rh)):
        if rels:
            print(f"**{title}:** " + ", ".join(f"`{r}`" for r in sorted(rels)) + NL)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: measure_diff.py <base-ref> <head-ref>")
    main(sys.argv[1], sys.argv[2])
