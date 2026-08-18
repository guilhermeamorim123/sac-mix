# Corretor de Redação — harness de calibração

Prova que uma foto de redação manuscrita vira nota confiável nas 5
competências do ENEM. Ver o design em
`../2026-08-17-redacao-todo-dia-design.md`.

## Rodar

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 run.py smoke                                # confirma chave e modelo
python3 run.py corrigir dataset/fotos/001.jpg --tema "..."
python3 run.py calibrar                             # roda o conjunto inteiro
```

A primeira execução cria `.venv/` automaticamente.

## Testes

```bash
.venv/bin/python -m pytest tests/ -v
```

Nenhum teste chama a API — todos usam cliente falso.

## O conjunto de calibração

`dataset/` está fora do git (redações de terceiros). Formato:

```
dataset/
├── gabarito.csv          arquivo,nota_total,c1,c2,c3,c4,c5,tema
└── fotos/001.jpg ...
```

Opcionalmente `dataset/transcricoes/001.txt` com o texto digitado à mão, para
medir a precisão da leitura da letra.
