# FEVEROUS pronto para grafos

Este projeto converte o dataset [FEVEROUS](https://fever.ai/dataset/feverous.html)
em CSVs para experimentos de grafos. Cada registro preserva a claim, o rótulo e
os conjuntos de evidência, incluindo o texto resolvido das evidências.

## Pré-requisitos

- Python 3.14 (ou outra versão compatível com as dependências deste projeto);
- acesso à internet no primeiro uso;
- pelo menos 64 GB livres em disco. O banco Wikipedia do FEVEROUS ocupa cerca
  de 10 GB compactado e aproximadamente 54 GB após extração.

## Instalação

No macOS ou Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps -r requirements.txt
```

No Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps -r requirements.txt
```

O projeto FEVEROUS é instalado diretamente do GitHub. O `--no-deps` evita os
pins antigos do repositório original; as dependências compatíveis necessárias
ao exportador já estão declaradas em `requirements.txt`.

## Execução

No macOS ou Linux:

```bash
.venv/bin/python run.py
```

No Windows:

```powershell
.\.venv\Scripts\python.exe run.py
```

`run.py` executa o fluxo completo:

1. verifica os arquivos do dataset em `data/`;
2. baixa os splits oficiais quando estiverem ausentes;
3. baixa e extrai o banco SQLite da Wikipedia;
4. chama `export_graph_ready_csv.py`.

Os dados baixados e CSVs gerados são ignorados pelo Git.

## Saídas

Depois da exportação, a pasta `processed-data/` contém:

```text
processed-data/
├── train.csv
├── test.csv
├── feverous_dataset_full.csv
└── feverous_dataset_full_interleaved.csv
```

Cada CSV tem as colunas:

```text
id,label,split,claim,evidence_text,evidence,evidence_annotation_id,
evidence_id,evidence_wiki_url,evidence_sentence_id
```

Os campos de evidência são JSON válido dentro da célula CSV. Em especial,
`evidence_text` usa o formato
`[{"set_id": 0, "text": ["trecho 1", "trecho 2"]}]`, em que cada objeto
representa uma alternativa completa de evidência.

## Arquivos principais

- `run.py`: download, validação e execução do pipeline;
- `export_graph_ready_csv.py`: geração dos CSVs prontos para grafos;
- `requirements.txt`: pacote FEVEROUS e dependências do exportador;
- `processed-data/README.md`: referência curta do esquema das saídas.
