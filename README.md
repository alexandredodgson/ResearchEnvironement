# ResearchEnvironement
Espace de recherche pour les systèmes agentiques.

## Arborescence

```
├── 01_knowledge/                  # 📚 Base de savoirs (Mémoire long terme)
│   ├── sources/                   # Synthèses d'articles, livres, fiches de lecture
│   ├── concepts/                  # Fiches atomiques / Zettelkasten interconnectés
│   └── INDEX                      # Carte de la base (générée par scripts/indexer.py)
│
├── 02_research/                   # 🔬 Projets & Axes de recherche en cours
│   └── axe-01-agentic_memory/     # Fichiers de travail par axe
│
├── 03_journal/                    # 📓 Journal de bord & Historique des sessions
│   ├── AAAA-MM-JJ.md              # Journal d'activité quotidien
│   └── ARCHIVE/
│
└── scripts/                       # ⚙️ Outils CLI d'assistance (Indexation/Search)
    ├── indexer.py                 # Indexation locale
    └── search.py                  # Recherche plein texte / vectorielle
```

## Scripts

```bash
# Régénérer l'index de la base de savoirs (01_knowledge/INDEX)
python3 scripts/indexer.py

# Recherche plein texte sur tout le dépôt
python3 scripts/search.py "mémoire agentique consolidation"

# Restreindre le scope / nombre de résultats
python3 scripts/search.py --scope 01_knowledge --top 5 "RAG graphe"

# Recherche vectorielle (nécessite sentence-transformers ; repli automatique sinon)
python3 scripts/search.py --vector "oubli sélectif"
```

## Conventions
- **Fiches de savoir** : Markdown avec frontmatter YAML optionnel (`title`, `description`, `tags`). À défaut, titre = premier `#`, tags = dièses inline (`#tag`).
- **Journal** : un fichier par jour (`03_journal/AAAA-MM-JJ.md`), archivés dans `03_journal/ARCHIVE/`.
- **Règle agents** : consulter `01_knowledge/INDEX` comme carte avant de lire les fiches en profondeur. 
