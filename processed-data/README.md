# CSV pronto para grafos

Na raiz desta pasta de trabalho, instale as dependências e execute:

```bash
python -m pip install --no-deps -r requirements.txt
python run.py
```

`run.py` verifica os arquivos necessários em `data/`, baixa somente
os que estiverem ausentes e então executa o exportador. Ele funciona em
Windows, Linux e macOS sem exigir `wget`, `curl` ou scripts de shell.

> O banco SQLite exige cerca de 54 GB após extração, além do ZIP de download
> de aproximadamente 10 GB. Garanta pelo menos 64 GB livres antes de rodar.

O comando cria:

```text
processed-data/
├── train.csv                              # 10.000 claims (5.000 SUPPORTS + 5.000 REFUTES)
├── test.csv                               # 3.000 claims (1.500 SUPPORTS + 1.500 REFUTES)
├── feverous_dataset_full.csv              # treino seguido de teste
└── feverous_dataset_full_interleaved.csv  # blocos de 10 treino + 3 teste
```

Cada linha segue o esquema do projeto FEVER de referência:

```text
id, label, split, claim, evidence_text, evidence,
evidence_annotation_id, evidence_id, evidence_wiki_url, evidence_sentence_id
```

Os campos de evidência são JSON válido dentro da célula CSV. Em particular,
`evidence_text` tem o formato `[{"set_id": 0, "text": ["trecho 1", "trecho 2"]}, ...]`.
Cada objeto representa uma alternativa completa de evidência; use `claim` e o
texto de cada conjunto para construir, respectivamente, os grafos da claim e
da evidência.
