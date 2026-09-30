#!/usr/bin/env python3
"""
search.py — Recherche plein texte sur l'ensemble du dépôt de recherche.

Parcourt tous les fichiers Markdown / texte (hors .git) et classe les fichiers
selon un score simple : fréquence des termes (TF) pondérée par une prime pour
les correspondances dans les titres, avec extraits de contexte autour des hits.

Mode vectoriel : optionnel, via --vector, si sentence-transformers est installé
(cosinus entre embedding de la requête et embeddings des paragraphes).

Usage :
    python3 scripts/search.py "mémoire agentique consolidation"
    python3 scripts/search.py --scope 01_knowledge "RAG graphe"
    python3 scripts/search.py --vector --top 5 "oubli sélectif"
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json"}
STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "à", "au", "aux",
    "en", "dans", "sur", "pour", "par", "avec", "sans", "que", "qui", "quoi",
    "dont", "où", "est", "sont", "ce", "cet", "cette", "ces", "the", "a", "an",
    "of", "in", "on", "for", "and", "or", "to", "is", "are",
}
WORD_RE = re.compile(r"[\wÀ-ÿ\-]{3,}", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS]


def iter_files(root: Path, scope: str | None):
    base = root
    if scope:
        base = root / scope
        if not base.is_dir():
            print(f"❌ Scope introuvable : {base}", file=sys.stderr)
            sys.exit(1)
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix in TEXT_SUFFIXES and ".git" not in p.parts:
            yield p


def snippet(text: str, terms: set[str], width: int = 140) -> str:
    low = text.lower()
    pos = -1
    for t in terms:
        i = low.find(t)
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return text[:width].strip()
    start = max(0, pos - width // 2)
    end = min(len(text), pos + width // 2)
    frag = re.sub(r"\s+", " ", text[start:end]).strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{frag}{suffix}"


def score_file(path: Path, query_terms: list[str], total_files: int) -> tuple[float, str] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    words = tokenize(text)
    if not words:
        return None
    counts = Counter(words)
    qset = set(query_terms)
    tf = sum(counts[t] for t in qset)
    if tf == 0:
        return None
    # Prime pour les titres
    headings = "\n".join(l for l in text.splitlines() if l.strip().startswith("#"))
    bonus = 3 * sum(1 for t in qset if t in headings.lower())
    idf = math.log(1 + total_files / (1 + tf))  # approximation légère
    score = (tf + bonus) * idf
    return score, snippet(text, qset)


def search_text(root: Path, query: str, scope: str | None, top: int) -> None:
    files = list(iter_files(root, scope))
    query_terms = tokenize(query)
    if not query_terms:
        print("Requête vide (stopwords uniquement).", file=sys.stderr)
        return
    results = []
    for f in files:
        r = score_file(f, query_terms, len(files))
        if r:
            results.append((r[0], f, r[1]))
    results.sort(key=lambda x: x[0], reverse=True)
    print(f"🔍 {len(results)} résultat(s) pour : « {query} »\n")
    for score, path, snip in results[:top]:
        rel = path.relative_to(root)
        print(f"▶ {rel}  (score {score:.1f})")
        print(f"  {snip}\n")


def search_vector(root: Path, query: str, scope: str | None, top: int) -> None:
    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore
    except ImportError:
        print("⚠️  sentence-transformers n'est pas installé. Repli sur la recherche plein texte.",
              file=sys.stderr)
        search_text(root, query, scope, top)
        return
    model = SentenceTransformer("all-MiniLM-L6-v2")
    passages: list[tuple[Path, str]] = []
    for f in iter_files(root, scope):
        text = f.read_text(encoding="utf-8", errors="replace")
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if len(para) > 80:
                passages.append((f, para))
    if not passages:
        print("Aucun passage à indexer.")
        return
    emb = model.encode([p for _, p in passages], convert_to_tensor=True)
    qemb = model.encode([query], convert_to_tensor=True)
    sims = util.cos_sim(qemb, emb)[0]
    ranked = sorted(range(len(passages)), key=lambda i: float(sims[i]), reverse=True)[:top]
    print(f"🧲 Recherche vectorielle — top {top} pour : « {query} »\n")
    for i in ranked:
        path, para = passages[i]
        rel = path.relative_to(root)
        print(f"▶ {rel}  (cos {(float(sims[i])):.3f})")
        print(f"  {re.sub(chr(10), ' ', para)[:160]}…\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recherche plein texte / vectorielle dans le dépôt.")
    parser.add_argument("query", help="Termes de recherche")
    parser.add_argument("--root", default=".", help="Racine du dépôt (défaut : courant)")
    parser.add_argument("--scope", help="Sous-répertoire limité (ex: 01_knowledge)")
    parser.add_argument("--top", type=int, default=10, help="Nombre de résultats (défaut : 10)")
    parser.add_argument("--vector", action="store_true", help="Active la recherche vectorielle (sentence-transformers)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.vector:
        search_vector(root, args.query, args.scope, args.top)
    else:
        search_text(root, args.query, args.scope, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
