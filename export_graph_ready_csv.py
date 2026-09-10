#!/usr/bin/env python3
"""Exporta anotações FEVEROUS para o CSV usado nos experimentos de grafos.

O arquivo de saída mantém uma linha por claim (como no projeto FEVER) e
preserva a estrutura completa de conjuntos de evidência em JSON. O campo
``evidence_text`` já contém o texto resolvido de sentenças, células, itens de
listas e captions, portanto pode ser usado diretamente para criar o grafo da
evidência sem voltar ao banco SQLite.
"""

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


# O exportador fica na raiz da área de trabalho; seus dados e saídas são
# resolvidos a partir deste diretório, independentemente de onde for executado.
WORKSPACE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = WORKSPACE_ROOT / "data"

from feverous.database.feverous_db import FeverousDB  # noqa: E402
from feverous.utils.util import get_evidence_text_by_id, get_wikipage_by_id  # noqa: E402


FIELDS = [
    "id", "label", "split", "claim", "evidence_text", "evidence",
    "evidence_annotation_id", "evidence_id", "evidence_wiki_url", "evidence_sentence_id",
]


def read_annotations(path: Path):
    """Lê JSONL nativo, ignorando o objeto inicial ``{\"header\": ...}``."""
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            annotation = json.loads(line)
            if line_number == 1 and "header" in annotation:
                continue
            if "claim" in annotation:
                yield annotation


def page_title(evidence_id: str) -> str:
    return evidence_id.split("_")[0]


def resolve_evidence(evidence_sets, database, page_cache):
    """Retorna texto, IDs e URLs de todas as alternativas de evidência."""
    rendered_sets = []
    all_ids, pages, sentence_ids = [], [], []
    resolved_text_count = 0

    for set_index, evidence_set in enumerate(evidence_sets):
        pieces = []
        for evidence_id in evidence_set.get("content", []):
            title = page_title(evidence_id)
            if title not in page_cache:
                try:
                    page_cache[title], _ = get_wikipage_by_id(evidence_id, database)
                except Exception:
                    page_cache[title] = None
            wiki_page = page_cache[title]
            try:
                text = get_evidence_text_by_id(evidence_id, wiki_page) if wiki_page else ""
            except Exception:
                text = ""
            if text:
                pieces.append(text)
                resolved_text_count += 1
            all_ids.append(evidence_id)
            if title not in pages:
                pages.append(title)
            if "_sentence_" in evidence_id:
                sentence_ids.append(evidence_id)
        rendered_sets.append({"set_id": set_index, "text": pieces})

    evidence_text = json.dumps(rendered_sets, ensure_ascii=False)
    urls = ["https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")) for title in pages]
    return evidence_text, all_ids, urls, sentence_ids, resolved_text_count


def make_rows(annotations, split, database):
    page_cache = {}
    rows = []
    for annotation in annotations:
        evidence_sets = annotation.get("evidence", [])
        evidence_text, ids, urls, sentence_ids, resolved_text_count = resolve_evidence(
            evidence_sets, database, page_cache
        )
        if not annotation.get("claim") or not ids or not resolved_text_count:
            continue
        rows.append({
            "id": annotation.get("id"), "label": annotation.get("label"), "split": split,
            "claim": annotation["claim"], "evidence_text": evidence_text,
            "evidence": json.dumps(evidence_sets, ensure_ascii=False),
            "evidence_annotation_id": json.dumps(list(range(len(evidence_sets))), ensure_ascii=False),
            "evidence_id": json.dumps(ids, ensure_ascii=False),
            "evidence_wiki_url": json.dumps(urls, ensure_ascii=False),
            "evidence_sentence_id": json.dumps(sentence_ids, ensure_ascii=False),
        })
    return rows


def balanced_sample(rows, labels, per_label, rng):
    grouped = defaultdict(list)
    for row in rows:
        if row["label"] in labels:
            grouped[row["label"]].append(row)
    missing = {label: per_label - len(grouped[label]) for label in labels if len(grouped[label]) < per_label}
    if missing:
        details = ", ".join(f"{label}: faltam {count}" for label, count in missing.items())
        raise ValueError(f"Não há exemplos suficientes após resolver as evidências ({details}).")
    for label in labels:
        rng.shuffle(grouped[label])
    return [grouped[label][index] for index in range(per_label) for label in labels]


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def interleave(train_rows, test_rows, train_block=10, test_block=3):
    result = []
    train_pos = test_pos = 0
    while train_pos < len(train_rows) or test_pos < len(test_rows):
        result.extend(train_rows[train_pos:train_pos + train_block])
        result.extend(test_rows[test_pos:test_pos + test_block])
        train_pos += train_block
        test_pos += test_block
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-input", type=Path, default=DATA_ROOT / "train.jsonl")
    parser.add_argument("--test-input", type=Path, default=DATA_ROOT / "dev.jsonl")
    parser.add_argument("--wiki-db", type=Path, default=DATA_ROOT / "feverous_wikiv1.db")
    parser.add_argument("--output-dir", type=Path, default=WORKSPACE_ROOT / "processed-data")
    parser.add_argument("--labels", nargs="+", default=["SUPPORTS", "REFUTES"])
    parser.add_argument("--train-per-label", type=int, default=5000)
    parser.add_argument("--test-per-label", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for required in (args.train_input, args.test_input, args.wiki_db):
        if not required.is_file():
            parser.error(f"Arquivo não encontrado: {required}")
    if args.train_per_label < 1 or args.test_per_label < 1:
        parser.error("Os tamanhos por rótulo devem ser positivos.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    with FeverousDB(str(args.wiki_db)) as database:
        train_all = make_rows(read_annotations(args.train_input), "train", database)
        test_all = make_rows(read_annotations(args.test_input), "test", database)

    train_rows = balanced_sample(train_all, args.labels, args.train_per_label, rng)
    test_rows = balanced_sample(test_all, args.labels, args.test_per_label, rng)
    write_csv(args.output_dir / "train.csv", train_rows)
    write_csv(args.output_dir / "test.csv", test_rows)
    write_csv(args.output_dir / "feverous_dataset_full.csv", train_rows + test_rows)
    write_csv(args.output_dir / "feverous_dataset_full_interleaved.csv", interleave(train_rows, test_rows))
    print(f"Exportados {len(train_rows)} exemplos de treino e {len(test_rows)} de teste em {args.output_dir}")


if __name__ == "__main__":
    main()
