#!/usr/bin/env python3
"""
indexer.py — Indexation locale de la base de savoirs (01_knowledge/)

Scanne les fiches Markdown de 01_knowledge/concepts/ et 01_knowledge/sources/,
extrait leurs métadonnées (frontmatter YAML ou première ligne de titre/description)
et régénère dynamiquement le fichier 01_knowledge/INDEX entre les balises :
    <!-- KNOWLEDGE_LIST_START --> ... <!-- KNOWLEDGE_LIST_END -->

La placeholder {{TIMESTAMP}} est remplacée par la date/heure de la dernière exécution.

Usage :
    python3 scripts/indexer.py [--root CHEMIN_DU_DEPOT]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

START_MARKER = "<!-- KNOWLEDGE_LIST_START -->"
END_MARKER = "<!-- KNOWLEDGE_LIST_END -->"
COMMENT_BLOCK_RE = re.compile(
    r"<!--\s*KNOWLEDGE_LIST_START\s*-->.*?<!--\s*KNOWLEDGE_LIST_END\s*-->",
    re.DOTALL,
)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
TAGS_INLINE_RE = re.compile(r"#([\w\-À-ÿ]+)")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Retourne (métadonnées, corps_du_texte) à partir d'un fichier Markdown."""
    meta: dict = {}
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip().strip("\"'[]{}")
                if key == "tags":
                    meta[key] = [t.strip().strip("\"'") for t in value.split(",") if t.strip()]
                else:
                    meta[key] = value
    return meta, body


def first_heading(body: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return ""


def first_paragraph(body: str) -> str:
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if b and not b.startswith("#") and not b.startswith("<!--"):
            return (b[:160] + "…") if len(b) > 160 else b
    return ""


def extract_tags(meta: dict, body: str, fallback_name: str) -> list[str]:
    tags = meta.get("tags") or []
    if not tags:
        tags = TAGS_INLINE_RE.findall(body)
    if not tags:
        tags = ["général"]
    # Déduplique en préservant l'ordre
    seen: set[str] = set()
    out = []
    for t in tags:
        t = t.strip().lstrip("#")
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def collect_entries(knowledge_dir: Path) -> list[dict]:
    entries = []
    for sub in ("concepts", "sources"):
        d = knowledge_dir / sub
        if not d.is_dir():
            continue
        for md in sorted(d.rglob("*.md")):
            text = md.read_text(encoding="utf-8", errors="replace")
            meta, body = parse_frontmatter(text)
            title = meta.get("title") or first_heading(body) or md.stem
            desc = meta.get("description") or first_paragraph(body)
            entries.append({
                "path": md.relative_to(knowledge_dir.parent),
                "name": md.name,
                "title": title,
                "description": desc,
                "tags": extract_tags(meta, body, md.stem),
                "category": sub,
            })
    return entries


def render_index(entries: list[dict]) -> str:
    by_tag: dict[str, list[dict]] = {}
    for e in entries:
        for t in e["tags"]:
            by_tag.setdefault(t, []).append(e)

    if not entries:
        return (
            f"{START_MARKER}\n"
            "_Aucune fiche trouvée dans `01_knowledge/concepts/` ou `01_knowledge/sources/`._\n"
            f"{END_MARKER}"
        )

    lines = [START_MARKER]
    for tag in sorted(by_tag, key=str.lower):
        lines.append(f"### 🏷️ #{tag}")
        for e in by_tag[tag]:
            desc = e["description"] or e["title"]
            lines.append(f"- `[{e['name']}]({e['path']})` : {desc}")
        lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexe la base de savoirs dans 01_knowledge/INDEX.")
    parser.add_argument("--root", default=".", help="Chemin racine du dépôt (défaut : courant)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    knowledge_dir = root / "01_knowledge"
    index_file = knowledge_dir / "INDEX"

    if not knowledge_dir.is_dir():
        print(f"❌ Répertoire introuvable : {knowledge_dir}", file=sys.stderr)
        return 1

    entries = collect_entries(knowledge_dir)

    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
    else:
        content = (
            "# 🧠 INDEX DE LA MÉMOIRE (KNOWLEDGE)\n"
            "> *Dernière mise à jour par script : {{TIMESTAMP}}*\n\n"
            "## 🗂️ Fiches de Savoirs Principales (par tags)\n\n"
            f"{START_MARKER}\n{END_MARKER}\n"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = content.replace("{{TIMESTAMP}}", now)

    new_block = render_index(entries)
    if START_MARKER in content and END_MARKER in content:
        content = COMMENT_BLOCK_RE.sub(new_block, content, count=1)
    else:
        content += "\n" + new_block + "\n"

    index_file.write_text(content, encoding="utf-8")
    print(f"✅ INDEX mis à jour : {len(entries)} fiche(s) indexée(s) → {index_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
