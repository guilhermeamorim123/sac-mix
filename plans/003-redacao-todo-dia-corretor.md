---
type: plan
name: "Corretor de Redação — Calibração (semana 1)"
project: "[[Redação Todo Dia]]"
owner: "[[Guilherme Figueredo]]"
date: 2026-08-17
status: pronto para executar
tags:
  - project/redacao-todo-dia
---

# Corretor de Redação — Plano de Implementação (semana 1)

> **Para quem for executar:** use `superpowers:subagent-driven-development`
> (recomendado) ou `superpowers:executing-plans` para tocar tarefa por tarefa.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Goal:** provar, até 24/08/2026, que uma foto de redação manuscrita vira nota
confiável nas 5 competências do ENEM — ou matar o projeto barato.

**Architecture:** CLI em Python que roda em duas etapas separadas — transcrição
da imagem e avaliação do texto — porque o maior risco técnico é o modelo ler a
letra errado e corrigir o texto errado. O julgamento de cada competência é do
modelo; a soma e as regras de anulação do ENEM ficam no código, porque são
determinísticas e é onde LLM erra de graça. Um harness de calibração roda o
conjunto de redações com nota conhecida e responde uma pergunta binária: o erro
médio está dentro da meta ou não.

**Tech Stack:** Python 3.9 (o do sistema), venv privado, SDK `anthropic`,
`claude-opus-5` com saída estruturada (`output_config.format`), pytest.

**Escopo:** só a semana 1 do spec. App, checkout, landing e os 60 temas ficam
para um plano seguinte, que só existe se este passar no critério da Tarefa 8.

**Spec:** [[2026-08-17-redacao-todo-dia-design]]

---

## Pré-requisitos (bloqueiam a Tarefa 1)

**1. Chave da API.** Não existe `ANTHROPIC_API_KEY` nesta máquina e o CLI `ant`
não está instalado, então não dá para usar login por perfil. Pegue uma chave em
`console.anthropic.com` → Settings → API Keys e exporte:

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

Confirme com `echo ${ANTHROPIC_API_KEY:0:12}` — deve imprimir `sk-ant-api03` ou
similar. **Nunca** escreva a chave em arquivo dentro do vault.

**2. O conjunto de calibração.** 20 redações com nota oficial conhecida,
cobrindo a faixa de 400 a 900 — não só as nota 1000 do INEP, que só dão a
âncora do teto. Fontes possíveis: cadernos de redação corrigida de cursinho,
simulados com espelho de correção, ou professores de redação. Cada item precisa
de: a foto (ou scan) e as 6 notas (total + as 5 competências).

Sem esse conjunto a Tarefa 8 não roda. Se conseguir só 10 redações, rode com
10 e trate o resultado como indicativo, não como veredito.

## Estrutura de arquivos

```
projects/redacao-todo-dia/corretor/
├── README.md          — como rodar
├── requirements.txt   — anthropic, pytest
├── conftest.py        — põe o diretório no sys.path do pytest
├── run.py             — CLI + bootstrap do venv
├── prompts.py         — rubrica das 5 competências e prompt de transcrição
├── schema.py          — JSON Schema da avaliação + regras duras do ENEM
├── api.py             — chamadas ao Claude e cálculo de custo
├── calibra.py         — laço do conjunto de teste e métricas
├── tests/
│   ├── test_schema.py
│   ├── test_api.py
│   └── test_calibra.py
└── dataset/           — fotos + gabarito.csv (fora do git)
```

Cada arquivo tem uma responsabilidade: `schema.py` não sabe que existe API,
`api.py` não sabe que existe calibração, e `calibra.py` não constrói prompt.
Isso é o que permite testar quase tudo sem gastar um centavo em chamada real.

---

### Task 1: Estrutura, venv e smoke test da API

**Files:**
- Create: `projects/redacao-todo-dia/corretor/requirements.txt`
- Create: `projects/redacao-todo-dia/corretor/conftest.py`
- Create: `projects/redacao-todo-dia/corretor/run.py`
- Create: `projects/redacao-todo-dia/corretor/README.md`
- Create: `projects/redacao-todo-dia/corretor/dataset/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Criar a estrutura de pastas**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
mkdir -p projects/redacao-todo-dia/corretor/tests
mkdir -p projects/redacao-todo-dia/corretor/dataset
touch projects/redacao-todo-dia/corretor/dataset/.gitkeep
```

- [ ] **Step 2: Manter o conjunto de redações fora do git**

As redações são de terceiros e as fotos podem identificar alunos. Acrescente ao
final de `.gitignore`:

```
# --- Redações do conjunto de calibração (dados de terceiros) ---
/projects/redacao-todo-dia/corretor/dataset/*
!/projects/redacao-todo-dia/corretor/dataset/.gitkeep
/projects/redacao-todo-dia/corretor/.venv/
```

- [ ] **Step 3: Escrever `requirements.txt`**

```
anthropic>=0.70
pytest>=8.0
```

- [ ] **Step 4: Escrever `conftest.py`**

```python
"""Presença deste arquivo faz o pytest pôr `corretor/` no sys.path.

Sem ele, `tests/test_schema.py` não consegue `import schema`, porque o pytest
insere o diretório do próprio teste no path, não o diretório pai.
"""
```

- [ ] **Step 5: Escrever `run.py` com o bootstrap do venv**

Mesmo padrão de `scripts/transcrever_audio.py`: cria um venv privado na
primeira execução e se re-executa dentro dele, para que o python do sistema
continue limpo.

```python
#!/usr/bin/env python3
"""Corretor de redação do ENEM — CLI de calibração.

Uso:
    python run.py smoke                      # confirma chave e modelo
    python run.py corrigir foto.jpg --tema "..."
    python run.py calibrar                   # roda o conjunto inteiro

A primeira execução cria um venv privado em `corretor/.venv/`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VENV = AQUI / ".venv"
VENV_PY = VENV / "bin" / "python"
REQUIREMENTS = AQUI / "requirements.txt"


def garante_venv() -> None:
    try:
        import anthropic  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("_CORRETOR_REEXEC"):
        sys.exit(f"Erro: anthropic não importa nem dentro do venv.\n"
                 f"Apague {VENV} e rode de novo.")

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.name}/ (só na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_CORRETOR_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def cria_cliente():
    import anthropic
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Erro: ANTHROPIC_API_KEY não está definida. Ver os pré-requisitos do plano.")
    return anthropic.Anthropic()


def cmd_smoke(args) -> None:
    cliente = cria_cliente()
    resposta = cliente.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Responda apenas: ok"}],
    )
    if resposta.stop_reason == "refusal":
        sys.exit(f"A API recusou: {resposta.stop_details}")
    texto = next(b.text for b in resposta.content if b.type == "text")
    print(f"modelo: {resposta.model}")
    print(f"resposta: {texto.strip()}")
    print(f"tokens: {resposta.usage.input_tokens} entrada / {resposta.usage.output_tokens} saída")


def main() -> None:
    garante_venv()

    parser = argparse.ArgumentParser(description="Corretor de redação do ENEM")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_smoke = sub.add_parser("smoke", help="confirma que a chave e o modelo respondem")
    p_smoke.set_defaults(func=cmd_smoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Rodar o smoke test**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff/projects/redacao-todo-dia/corretor"
python3 run.py smoke
```

Esperado (a primeira execução leva ~1 min instalando o venv):

```
modelo: claude-opus-5
resposta: ok
tokens: 13 entrada / 5 saída
```

Se der `ANTHROPIC_API_KEY não está definida`, volte aos pré-requisitos. Se der
404 no modelo, a chave não tem acesso ao Opus 5 — troque para
`claude-sonnet-5` em `run.py` e anote, porque isso muda a Tarefa 5.

- [ ] **Step 7: Escrever o `README.md`**

````markdown
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
````

- [ ] **Step 8: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add .gitignore projects/redacao-todo-dia/corretor/
git commit -m "feat(corretor): estrutura, venv e smoke test da API"
```

---

### Task 2: `schema.py` — contrato da avaliação e as regras duras do ENEM

O modelo julga cada competência. A soma e as regras de anulação são nossas.

**Files:**
- Create: `projects/redacao-todo-dia/corretor/schema.py`
- Test: `projects/redacao-todo-dia/corretor/tests/test_schema.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Testes das regras de anulação do ENEM — a parte que não pode errar."""

import pytest

import schema


def avaliacao(notas=(160, 160, 160, 160, 160), linhas=25, enquadramento="ok"):
    """Monta uma avaliação crua, como o modelo devolveria."""
    return {
        "competencias": [
            {"numero": n, "nota": nota, "justificativa": "...", "melhorias": ["a", "b"]}
            for n, nota in enumerate(notas, start=1)
        ],
        "linhas": linhas,
        "enquadramento": enquadramento,
        "resumo": "...",
    }


def test_soma_as_cinco_competencias():
    resultado = schema.normaliza(avaliacao(notas=(200, 160, 120, 80, 40)))
    assert resultado["nota_total"] == 600
    assert resultado["penalidade"] is None


def test_ate_sete_linhas_anula_a_redacao():
    resultado = schema.normaliza(avaliacao(linhas=7))
    assert resultado["nota_total"] == 0
    assert all(c["nota"] == 0 for c in resultado["competencias"])
    assert "7 linhas" in resultado["penalidade"]


def test_oito_linhas_nao_anula():
    resultado = schema.normaliza(avaliacao(linhas=8))
    assert resultado["nota_total"] == 800


def test_fuga_total_ao_tema_anula_a_redacao_inteira():
    resultado = schema.normaliza(avaliacao(enquadramento="fuga_total"))
    assert resultado["nota_total"] == 0
    assert "fuga" in resultado["penalidade"]


def test_texto_nao_dissertativo_anula():
    resultado = schema.normaliza(avaliacao(enquadramento="nao_dissertativo"))
    assert resultado["nota_total"] == 0


def test_copia_do_texto_motivador_anula():
    resultado = schema.normaliza(avaliacao(enquadramento="copia_motivador"))
    assert resultado["nota_total"] == 0


def test_tangenciamento_nao_anula():
    """A confusão mais comum: tangenciar não é fugir. Penaliza C2/C3, não zera."""
    resultado = schema.normaliza(avaliacao(notas=(160, 40, 40, 160, 160),
                                           enquadramento="tangenciamento"))
    assert resultado["nota_total"] == 560
    assert resultado["penalidade"] is None


def test_recusa_avaliacao_sem_as_cinco_competencias():
    crua = avaliacao()
    crua["competencias"] = crua["competencias"][:4]
    with pytest.raises(ValueError, match="5 competências"):
        schema.normaliza(crua)


def test_recusa_competencia_repetida():
    crua = avaliacao()
    crua["competencias"][4]["numero"] = 1
    with pytest.raises(ValueError, match="5 competências"):
        schema.normaliza(crua)


def test_competencias_saem_ordenadas():
    crua = avaliacao()
    crua["competencias"].reverse()
    resultado = schema.normaliza(crua)
    assert [c["numero"] for c in resultado["competencias"]] == [1, 2, 3, 4, 5]


def test_schema_nao_usa_recursos_nao_suportados():
    """A API rejeita minimum/maximum/minLength — o grid de notas vira enum."""
    texto = repr(schema.AVALIACAO_SCHEMA)
    for proibido in ("minimum", "maximum", "minLength", "maxLength", "multipleOf"):
        assert proibido not in texto
    assert schema.AVALIACAO_SCHEMA["additionalProperties"] is False


def test_schema_nao_pede_nota_total_ao_modelo():
    """Somar é nosso. Se o modelo somasse, teria como errar."""
    assert "nota_total" not in schema.AVALIACAO_SCHEMA["properties"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff/projects/redacao-todo-dia/corretor"
.venv/bin/python -m pytest tests/test_schema.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'schema'`.

- [ ] **Step 3: Escrever `schema.py`**

```python
"""Contrato da avaliação e as regras de anulação do ENEM.

O modelo julga cada competência. A aritmética e os zeramentos ficam aqui,
porque são determinísticos: somar cinco números é onde LLM erra sem ganhar
nada em troca.
"""

from __future__ import annotations

COMPETENCIAS = {
    1: "Domínio da modalidade escrita formal da língua portuguesa",
    2: "Compreender a proposta e aplicar conceitos de várias áreas do conhecimento",
    3: "Selecionar, relacionar, organizar e interpretar informações em defesa de um ponto de vista",
    4: "Conhecimento dos mecanismos linguísticos de construção da argumentação",
    5: "Elaborar proposta de intervenção que respeite os direitos humanos",
}

# O ENEM só dá nota em múltiplos de 40, de 0 a 200, por competência.
NOTAS_VALIDAS = [0, 40, 80, 120, 160, 200]

# Enquadramentos que anulam a redação inteira. Tangenciamento NÃO está aqui:
# tangenciar penaliza as competências 2 e 3 dentro da escala normal.
ANULA = {
    "fuga_total": "fuga total ao tema",
    "nao_dissertativo": "texto não é dissertativo-argumentativo",
    "copia_motivador": "cópia dos textos motivadores",
}

ENQUADRAMENTOS = ["ok", "tangenciamento", *ANULA.keys()]

LINHAS_MINIMAS = 8  # "até 7 linhas" anula; 8 já vale

AVALIACAO_SCHEMA = {
    "type": "object",
    "properties": {
        "competencias": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                    "nota": {"type": "integer", "enum": NOTAS_VALIDAS},
                    "justificativa": {"type": "string"},
                    "melhorias": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["numero", "nota", "justificativa", "melhorias"],
                "additionalProperties": False,
            },
        },
        "linhas": {"type": "integer"},
        "enquadramento": {"type": "string", "enum": ENQUADRAMENTOS},
        "resumo": {"type": "string"},
    },
    "required": ["competencias", "linhas", "enquadramento", "resumo"],
    "additionalProperties": False,
}


def normaliza(avaliacao: dict) -> dict:
    """Aplica as regras de anulação e calcula a nota total.

    Devolve um dicionário novo com `nota_total` e `penalidade` (None quando
    nada foi anulado). Levanta ValueError se o modelo não devolveu exatamente
    as 5 competências.
    """
    por_numero = {c["numero"]: dict(c) for c in avaliacao["competencias"]}
    if sorted(por_numero) != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"esperava as 5 competências, veio {sorted(por_numero)}"
        )

    penalidade = None
    if avaliacao["linhas"] < LINHAS_MINIMAS:
        penalidade = "até 7 linhas: redação anulada"
    elif avaliacao["enquadramento"] in ANULA:
        penalidade = f"{ANULA[avaliacao['enquadramento']]}: redação anulada"

    if penalidade:
        for numero in por_numero:
            por_numero[numero]["nota"] = 0

    return {
        **avaliacao,
        "competencias": [por_numero[n] for n in (1, 2, 3, 4, 5)],
        "nota_total": sum(c["nota"] for c in por_numero.values()),
        "penalidade": penalidade,
    }
```

- [ ] **Step 4: Rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/test_schema.py -v
```

Esperado: 12 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/schema.py projects/redacao-todo-dia/corretor/tests/test_schema.py
git commit -m "feat(corretor): schema da avaliacao e regras de anulacao do ENEM"
```

---

### Task 3: `prompts.py` — a rubrica

A rubrica é o bloco estável de toda requisição de avaliação, e é o que vai para
o cache. Ela precisa ser longa e específica: é ela que separa uma nota
calibrada de um chute educado.

**Files:**
- Create: `projects/redacao-todo-dia/corretor/prompts.py`
- Modify: `projects/redacao-todo-dia/corretor/tests/test_schema.py` (acrescenta um bloco no fim)

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao final de `tests/test_schema.py`:

```python
# --- prompts -------------------------------------------------------------

import prompts


def test_rubrica_cobre_as_cinco_competencias():
    for numero in (1, 2, 3, 4, 5):
        assert f"Competência {numero}" in prompts.RUBRICA


def test_rubrica_ensina_a_diferenca_entre_fuga_e_tangenciamento():
    assert "tangenciamento" in prompts.RUBRICA.lower()
    assert "fuga total" in prompts.RUBRICA.lower()


def test_rubrica_proibe_o_modelo_de_somar():
    assert "não some" in prompts.RUBRICA.lower()


def test_rubrica_e_grande_o_bastante_para_cachear():
    """O mínimo cacheável no Opus 5 é 512 tokens (~2000 caracteres)."""
    assert len(prompts.RUBRICA) > 2500


def test_prompt_de_transcricao_proibe_avaliar():
    assert "não avalie" in prompts.TRANSCRICAO.lower()


def test_prompt_de_transcricao_pede_fidelidade_aos_erros():
    assert "não corrija" in prompts.TRANSCRICAO.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/test_schema.py -v -k "rubrica or transcricao"
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'prompts'`.

- [ ] **Step 3: Escrever `prompts.py`**

```python
"""Os dois prompts do corretor.

RUBRICA é o bloco estável enviado em toda avaliação — é o que vai para o cache.
TRANSCRICAO é deliberadamente curto e faz uma coisa só: ler a letra.
"""

from __future__ import annotations

TRANSCRICAO = """Você recebe a foto de uma redação manuscrita do ENEM.

Sua única tarefa é transcrever o texto exatamente como está escrito.

- Não avalie, não comente, não explique. Devolva apenas o texto.
- Não corrija erros de ortografia, gramática, concordância ou pontuação. Se o \
aluno escreveu "menas", transcreva "menas". Os erros são o que vai ser \
avaliado depois — corrigir aqui destrói a avaliação.
- Preserve a quebra de parágrafos.
- Se uma palavra estiver genuinamente ilegível, escreva [ilegível] no lugar. \
Não invente a palavra que faria sentido.
- Se a foto estiver cortada ou ilegível a ponto de não dar para transcrever, \
responda apenas: FOTO_ILEGIVEL
- Na primeira linha, escreva LINHAS: <número de linhas escritas>, depois uma \
linha em branco, e então o texto."""


RUBRICA = """Você é corretor de redação do ENEM. Avalia com o rigor e a \
calibração de um corretor experiente do INEP — nem generoso, nem punitivo.

Você recebe o texto já transcrito de uma redação e o tema proposto. Avalia as \
cinco competências, cada uma de 0 a 200, apenas em múltiplos de 40 \
(0, 40, 80, 120, 160, 200).

# Competência 1 — Domínio da modalidade escrita formal
Ortografia, acentuação, concordância, regência, pontuação, colocação \
pronominal, separação silábica.
- 200: no máximo um desvio, e leve.
- 160: poucos desvios, nenhum grave.
- 120: desvios frequentes, mas o texto se lê sem esforço.
- 80: desvios que atrapalham a leitura.
- 40: texto precário.
- 0: desconhecimento da norma escrita.
Marca registrada do erro de calibração: dar 200 para texto com dois ou três \
desvios. Se você encontrou dois desvios, a nota é 160.

# Competência 2 — Compreender a proposta e aplicar repertório
Abordagem do tema, uso do tipo textual dissertativo-argumentativo, e \
repertório sociocultural produtivo (citação, dado, obra, fato histórico) que \
seja legitimado, pertinente ao tema e usado para argumentar — não enfeite.
- 200: tema abordado com precisão, estrutura dissertativa completa \
(introdução com tese, desenvolvimento, conclusão), pelo menos um repertório \
legitimado e produtivo.
- 160: tema abordado, estrutura completa, repertório presente mas pouco \
explorado.
- 120: tema abordado, repertório ausente ou baseado só nos textos motivadores.
- 80: tangencia o tema.
- 40: texto embrionário ou predominantemente de outro tipo textual.
Repertório copiado dos textos motivadores NÃO conta. Repertório citado sem \
ligação com o argumento vale menos que repertório usado para sustentar a tese.

# Competência 3 — Selecionar, relacionar e organizar informações
Projeto de texto: os argumentos sustentam a tese, estão em ordem, e cada \
parágrafo desenvolve o que anuncia.
- 200: projeto de texto claro, argumentos desenvolvidos com autoria.
- 160: projeto claro, um argumento pouco desenvolvido.
- 120: argumentos previsíveis ou desenvolvidos por repetição.
- 80: informações pouco relacionadas ao ponto de vista.
- 40: tangencia.
Pergunte-se: se eu tirasse o segundo parágrafo, o texto perderia alguma coisa? \
Se não perderia, o parágrafo não desenvolveu nada.

# Competência 4 — Mecanismos linguísticos de coesão
Conectivos entre parágrafos e dentro deles, referenciação (pronomes, \
sinônimos, elipses) sem repetição desnecessária.
- 200: repertório diversificado de conectivos, sem repetição.
- 160: bom uso, com alguma repetição.
- 120: uso mediano, conectivos repetidos.
- 80: uso pontual.
- 40: raro.
Começar três parágrafos com "Além disso" é o padrão de 120, não de 160.

# Competência 5 — Proposta de intervenção
Precisa ter cinco elementos: agente (quem faz), ação (o que faz), modo/meio \
(como), efeito (para quê) e detalhamento (de qualquer um dos anteriores). E \
precisa respeitar os direitos humanos.
- 200: os cinco elementos, articulados ao problema discutido no texto.
- 160: quatro elementos.
- 120: três elementos.
- 80: dois elementos.
- 40: um elemento, ou proposta vaga ("é preciso conscientizar a população").
- 0: sem proposta, ou proposta que viola direitos humanos.
"O governo deve investir em educação" tem agente e ação, e nada mais: 80.

# Enquadramento — a distinção que mais se erra
Devolva um destes valores em `enquadramento`:
- `ok`: o texto aborda o tema proposto.
- `tangenciamento`: aborda o assunto mais amplo mas não o recorte específico \
do tema. NÃO anula: penaliza as competências 2 e 3 dentro da escala normal.
- `fuga_total`: o texto trata de outro tema. Anula a redação.
- `nao_dissertativo`: é narração, poema, receita, carta. Anula.
- `copia_motivador`: é cópia dos textos motivadores, sem produção própria. \
Anula.
Na dúvida entre `tangenciamento` e `fuga_total`, escolha `tangenciamento`. \
Anular uma redação que só tangenciou é o erro mais caro que um corretor comete.

# Contagem de linhas
Devolva em `linhas` quantas linhas escritas o texto tem. Até 7 linhas a \
redação é anulada — mas você não aplica essa regra, apenas informa o número.

# Regras da sua saída
- Não some as notas. Não devolva nota total. A soma é feita fora daqui.
- Não aplique zeramentos. Informe `enquadramento` e `linhas`; quem anula é o \
código que recebe sua resposta.
- Em `justificativa`, diga o que o texto fez, citando trecho quando ajudar. \
Não repita a descrição da competência.
- Em `melhorias`, dê exatamente duas ações concretas que o aluno faria na \
próxima redação. "Melhore a coesão" não é ação. "Troque o 'Além disso' do \
terceiro parágrafo por uma conclusão que retome a tese" é ação.
- Escreva para um aluno de 17 anos: direto, sem jargão de corretor, sem \
gentileza vazia."""
```

- [ ] **Step 4: Rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/test_schema.py -v
```

Esperado: 18 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/prompts.py projects/redacao-todo-dia/corretor/tests/test_schema.py
git commit -m "feat(corretor): rubrica das 5 competencias e prompt de transcricao"
```

---

### Task 4: `api.py` — transcrição da imagem

**Files:**
- Create: `projects/redacao-todo-dia/corretor/api.py`
- Test: `projects/redacao-todo-dia/corretor/tests/test_api.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Testes das chamadas à API — todos com cliente falso, nenhum gasta dinheiro."""

import base64
from types import SimpleNamespace

import pytest

import api


class FakeMessages:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamada = None

    def create(self, **kwargs):
        self.chamada = kwargs
        return self.resposta


class FakeClient:
    def __init__(self, resposta):
        self.messages = FakeMessages(resposta)


def uso(entrada=100, saida=50, escrita_cache=0, leitura_cache=0):
    return SimpleNamespace(
        input_tokens=entrada,
        output_tokens=saida,
        cache_creation_input_tokens=escrita_cache,
        cache_read_input_tokens=leitura_cache,
    )


def resposta(texto, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=None,
        model="claude-opus-5",
        content=[SimpleNamespace(type="text", text=texto)],
        usage=uso(),
    )


def foto_falsa(tmp_path, nome="redacao.jpg"):
    caminho = tmp_path / nome
    caminho.write_bytes(b"\xff\xd8\xff\xe0conteudo-jpeg-falso")
    return caminho


# --- bloco de imagem -----------------------------------------------------

def test_bloco_imagem_codifica_em_base64(tmp_path):
    caminho = foto_falsa(tmp_path)
    bloco = api._bloco_imagem(caminho)
    assert bloco["type"] == "image"
    assert bloco["source"]["media_type"] == "image/jpeg"
    assert base64.standard_b64decode(bloco["source"]["data"]) == caminho.read_bytes()


def test_bloco_imagem_rejeita_formato_nao_suportado(tmp_path):
    caminho = tmp_path / "redacao.pdf"
    caminho.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="formato"):
        api._bloco_imagem(caminho)


# --- transcrever ---------------------------------------------------------

def test_transcrever_devolve_texto_e_linhas(tmp_path):
    cliente = FakeClient(resposta("LINHAS: 24\n\nA educação é um direito."))
    resultado, _ = api.transcrever(cliente, foto_falsa(tmp_path))
    assert resultado.linhas == 24
    assert resultado.texto == "A educação é um direito."


def test_transcrever_envia_a_imagem_para_o_modelo_certo(tmp_path):
    cliente = FakeClient(resposta("LINHAS: 10\n\ntexto"))
    api.transcrever(cliente, foto_falsa(tmp_path))
    enviado = cliente.messages.chamada
    assert enviado["model"] == api.MODELO
    blocos = enviado["messages"][0]["content"]
    assert any(b["type"] == "image" for b in blocos)


def test_transcrever_avisa_quando_a_foto_esta_ilegivel(tmp_path):
    cliente = FakeClient(resposta("FOTO_ILEGIVEL"))
    with pytest.raises(api.FotoIlegivel):
        api.transcrever(cliente, foto_falsa(tmp_path))


def test_transcrever_levanta_erro_em_recusa(tmp_path):
    cliente = FakeClient(resposta("", stop_reason="refusal"))
    with pytest.raises(api.RecusaDaAPI):
        api.transcrever(cliente, foto_falsa(tmp_path))


def test_transcrever_aceita_texto_sem_cabecalho_de_linhas(tmp_path):
    """Se o modelo esquecer o cabeçalho, contamos as linhas nós mesmos."""
    cliente = FakeClient(resposta("primeira linha\nsegunda linha"))
    resultado, _ = api.transcrever(cliente, foto_falsa(tmp_path))
    assert resultado.linhas == 2
    assert resultado.texto == "primeira linha\nsegunda linha"
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/test_api.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'api'`.

- [ ] **Step 3: Escrever `api.py` (parte da transcrição)**

```python
"""Chamadas ao Claude: transcrever a foto e avaliar o texto.

As duas etapas são separadas de propósito. O maior risco técnico do produto é
o modelo ler a letra errado; separando, o erro de leitura vira uma tela de
conferência de dez segundos em vez de uma correção errada.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path

import prompts
import schema

MODELO = "claude-opus-5"
MAX_TOKENS = 16000

FORMATOS_ACEITOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class RecusaDaAPI(RuntimeError):
    """A API recusou a requisição (stop_reason == 'refusal')."""


class FotoIlegivel(ValueError):
    """O modelo não conseguiu ler a foto."""


@dataclass
class Transcricao:
    texto: str
    linhas: int


def _bloco_imagem(caminho: Path) -> dict:
    media_type, _ = mimetypes.guess_type(caminho.name)
    if media_type not in FORMATOS_ACEITOS:
        raise ValueError(
            f"formato não suportado: {caminho.name} ({media_type}). "
            f"Aceitos: {', '.join(sorted(FORMATOS_ACEITOS))}"
        )
    dados = base64.standard_b64encode(caminho.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": dados},
    }


def _texto_da_resposta(resposta) -> str:
    if resposta.stop_reason == "refusal":
        raise RecusaDaAPI(f"a API recusou: {resposta.stop_details}")
    return next(b.text for b in resposta.content if b.type == "text")


def transcrever(cliente, caminho: Path):
    """Lê a foto e devolve (Transcricao, usage). Não avalia nada."""
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [_bloco_imagem(Path(caminho)),
                        {"type": "text", "text": prompts.TRANSCRICAO}],
        }],
    )
    bruto = _texto_da_resposta(resposta).strip()

    if bruto.startswith("FOTO_ILEGIVEL"):
        raise FotoIlegivel(f"o modelo não conseguiu ler {Path(caminho).name}")

    cabecalho = re.match(r"^LINHAS:\s*(\d+)\s*\n+", bruto)
    if cabecalho:
        linhas = int(cabecalho.group(1))
        texto = bruto[cabecalho.end():].strip()
    else:
        texto = bruto
        linhas = len([l for l in texto.splitlines() if l.strip()])

    return Transcricao(texto=texto, linhas=linhas), resposta.usage
```

- [ ] **Step 4: Rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/test_api.py -v
```

Esperado: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/api.py projects/redacao-todo-dia/corretor/tests/test_api.py
git commit -m "feat(corretor): transcricao da foto manuscrita"
```

---

### Task 5: `api.py` — avaliação estruturada e custo

**Files:**
- Modify: `projects/redacao-todo-dia/corretor/api.py`
- Modify: `projects/redacao-todo-dia/corretor/tests/test_api.py`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao final de `tests/test_api.py`:

```python
# --- avaliar -------------------------------------------------------------

import json

import prompts
import schema


def avaliacao_json(nota=160, enquadramento="ok", linhas=25):
    return json.dumps({
        "competencias": [
            {"numero": n, "nota": nota, "justificativa": "j", "melhorias": ["a", "b"]}
            for n in (1, 2, 3, 4, 5)
        ],
        "linhas": linhas,
        "enquadramento": enquadramento,
        "resumo": "r",
    })


def test_avaliar_devolve_avaliacao_normalizada():
    cliente = FakeClient(resposta(avaliacao_json(nota=160)))
    resultado, _ = api.avaliar(cliente, "texto da redação", "Tema qualquer")
    assert resultado["nota_total"] == 800
    assert resultado["penalidade"] is None


def test_avaliar_aplica_as_regras_de_anulacao():
    cliente = FakeClient(resposta(avaliacao_json(nota=200, enquadramento="fuga_total")))
    resultado, _ = api.avaliar(cliente, "texto", "Tema")
    assert resultado["nota_total"] == 0


def test_avaliar_exige_saida_estruturada():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto", "Tema")
    enviado = cliente.messages.chamada
    assert enviado["output_config"]["format"]["type"] == "json_schema"
    assert enviado["output_config"]["format"]["schema"] == schema.AVALIACAO_SCHEMA


def test_avaliar_cacheia_a_rubrica():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto", "Tema")
    bloco_sistema = cliente.messages.chamada["system"][0]
    assert bloco_sistema["text"] == prompts.RUBRICA
    assert bloco_sistema["cache_control"] == {"type": "ephemeral"}


def test_avaliar_manda_o_tema_junto():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto da redação", "Desafios da mobilidade urbana")
    conteudo = cliente.messages.chamada["messages"][0]["content"]
    assert "Desafios da mobilidade urbana" in conteudo
    assert "texto da redação" in conteudo


def test_avaliar_levanta_erro_em_recusa():
    cliente = FakeClient(resposta("", stop_reason="refusal"))
    with pytest.raises(api.RecusaDaAPI):
        api.avaliar(cliente, "texto", "Tema")


# --- custo ---------------------------------------------------------------

def test_custo_de_um_milhao_de_tokens_de_entrada():
    assert api.custo_usd(uso(entrada=1_000_000, saida=0)) == pytest.approx(5.00)


def test_custo_de_um_milhao_de_tokens_de_saida():
    assert api.custo_usd(uso(entrada=0, saida=1_000_000)) == pytest.approx(25.00)


def test_leitura_de_cache_custa_um_decimo_da_entrada():
    assert api.custo_usd(uso(entrada=0, saida=0, leitura_cache=1_000_000)) == pytest.approx(0.50)


def test_escrita_de_cache_custa_1_25_vezes_a_entrada():
    assert api.custo_usd(uso(entrada=0, saida=0, escrita_cache=1_000_000)) == pytest.approx(6.25)


def test_custo_tolera_usage_sem_campos_de_cache():
    """Nem toda resposta traz os campos de cache."""
    magro = SimpleNamespace(input_tokens=1_000_000, output_tokens=0)
    assert api.custo_usd(magro) == pytest.approx(5.00)
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/test_api.py -v -k "avaliar or custo or cache"
```

Esperado: FAIL com `AttributeError: module 'api' has no attribute 'avaliar'`.

- [ ] **Step 3: Acrescentar a avaliação e o custo em `api.py`**

Acrescente ao final de `api.py`:

```python
# Preço do claude-opus-5 em USD por 1M de tokens (referência de 17/08/2026).
PRECO_ENTRADA = 5.00
PRECO_SAIDA = 25.00
FATOR_ESCRITA_CACHE = 1.25
FATOR_LEITURA_CACHE = 0.10


def avaliar(cliente, texto: str, tema: str):
    """Avalia o texto transcrito. Devolve (avaliação normalizada, usage)."""
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=[{
            "type": "text",
            "text": prompts.RUBRICA,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": (
                f"TEMA PROPOSTO:\n{tema}\n\n"
                f"REDAÇÃO DO ALUNO (transcrita da foto):\n{texto}"
            ),
        }],
        output_config={
            "format": {"type": "json_schema", "schema": schema.AVALIACAO_SCHEMA}
        },
    )
    crua = json.loads(_texto_da_resposta(resposta))
    return schema.normaliza(crua), resposta.usage


def custo_usd(usage) -> float:
    """Custo da chamada em dólares, a partir do objeto `usage` da resposta."""
    escrita_cache = getattr(usage, "cache_creation_input_tokens", 0) or 0
    leitura_cache = getattr(usage, "cache_read_input_tokens", 0) or 0
    entrada = (
        usage.input_tokens
        + escrita_cache * FATOR_ESCRITA_CACHE
        + leitura_cache * FATOR_LEITURA_CACHE
    )
    return entrada * PRECO_ENTRADA / 1e6 + usage.output_tokens * PRECO_SAIDA / 1e6
```

- [ ] **Step 4: Rodar a suíte inteira**

```bash
.venv/bin/python -m pytest tests/ -v
```

Esperado: 36 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/api.py projects/redacao-todo-dia/corretor/tests/test_api.py
git commit -m "feat(corretor): avaliacao estruturada com cache da rubrica e calculo de custo"
```

---

### Task 6: `run.py corrigir` — o fluxo de duas etapas com confirmação

É aqui que você vê o produto pela primeira vez. Use a sua letra, e depois a
letra mais feia que conseguir arranjar.

**Files:**
- Modify: `projects/redacao-todo-dia/corretor/run.py`

- [ ] **Step 1: Acrescentar o comando em `run.py`**

Acrescente antes da função `main()`:

```python
def cmd_corrigir(args) -> None:
    import api

    cliente = cria_cliente()
    caminho = Path(args.foto)

    print(f"Lendo {caminho.name}...")
    transcricao, uso_transcricao = api.transcrever(cliente, caminho)

    print(f"\n--- TRANSCRIÇÃO ({transcricao.linhas} linhas) ---")
    print(transcricao.texto)
    print("--- fim ---\n")

    if not args.sem_confirmar:
        resposta = input("Li a letra direito? [S/n] ").strip().lower()
        if resposta and resposta not in ("s", "sim"):
            print("\nCorrija a transcrição num editor e rode de novo com "
                  "--texto arquivo.txt quando isso existir. Por enquanto, "
                  "tire outra foto com mais luz.")
            return

    print("Avaliando...")
    avaliacao, uso_avaliacao = api.avaliar(cliente, transcricao.texto, args.tema)

    print(f"\n=== NOTA: {avaliacao['nota_total']} ===")
    if avaliacao["penalidade"]:
        print(f"!! {avaliacao['penalidade']}")
    print(f"enquadramento: {avaliacao['enquadramento']}\n")

    for competencia in avaliacao["competencias"]:
        print(f"C{competencia['numero']}: {competencia['nota']}")
        print(f"   {competencia['justificativa']}")
        for melhoria in competencia["melhorias"]:
            print(f"   → {melhoria}")
        print()

    print(avaliacao["resumo"])

    custo = api.custo_usd(uso_transcricao) + api.custo_usd(uso_avaliacao)
    print(f"\ncusto desta correção: US$ {custo:.4f}")
```

E dentro de `main()`, antes de `args = parser.parse_args()`:

```python
    p_corrigir = sub.add_parser("corrigir", help="corrige uma foto de redação")
    p_corrigir.add_argument("foto", help="caminho da foto")
    p_corrigir.add_argument("--tema", required=True, help="tema proposto da redação")
    p_corrigir.add_argument("--sem-confirmar", action="store_true",
                            dest="sem_confirmar",
                            help="pula a conferência da transcrição")
    p_corrigir.set_defaults(func=cmd_corrigir)
```

- [ ] **Step 2: Testar com a sua própria letra**

Escreva uma redação de ~25 linhas à mão sobre um tema qualquer, fotografe com o
celular (luz de cima, folha reta) e rode:

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff/projects/redacao-todo-dia/corretor"
python3 run.py corrigir ~/Desktop/minha-redacao.jpg \
  --tema "Desafios para a valorização do professor no Brasil"
```

Esperado: a transcrição sai fiel (inclusive os erros), você confirma, e a nota
sai com justificativa por competência e duas ações concretas em cada uma. O
custo impresso no fim deve ficar entre US$ 0,05 e US$ 0,12.

- [ ] **Step 3: Testar com letra ruim**

Repita com a pior letra que conseguir arranjar. **Este é o teste que importa.**
Se a transcrição vier com muitos `[ilegível]` ou trocar palavras, anote quais
fotos falharam — isso vira o conjunto de OCR da Tarefa 8.

- [ ] **Step 4: Testar uma redação curta**

Escreva 6 linhas e rode. Esperado: `NOTA: 0` e `!! até 7 linhas: redação
anulada`.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/run.py
git commit -m "feat(corretor): comando corrigir com confirmacao da transcricao"
```

---

### Task 7: `calibra.py` — as métricas

**Files:**
- Create: `projects/redacao-todo-dia/corretor/calibra.py`
- Test: `projects/redacao-todo-dia/corretor/tests/test_calibra.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Testes das métricas de calibração — funções puras, sem API."""

import csv

import pytest

import calibra


def test_erro_medio_absoluto():
    assert calibra.mae([(700, 660), (500, 580)]) == 60.0


def test_erro_medio_absoluto_de_lista_vazia_e_zero():
    assert calibra.mae([]) == 0.0


def test_vies_mostra_se_o_corretor_e_generoso_ou_duro():
    """Positivo = o modelo dá nota acima da oficial."""
    assert calibra.vies([(700, 760), (500, 560)]) == 60.0
    assert calibra.vies([(700, 640), (500, 440)]) == -60.0


def test_acuracia_ocr_ignora_pontuacao_e_caixa():
    assert calibra.acuracia_ocr(
        "A educação, é um direito!", "a educação é um direito"
    ) == pytest.approx(1.0)


def test_acuracia_ocr_penaliza_palavra_trocada():
    assert calibra.acuracia_ocr("a casa é azul", "a casa é verde") == pytest.approx(0.75)


def test_acuracia_ocr_nao_ignora_acento():
    """Acento errado é erro de competência 1 — não pode ser mascarado aqui."""
    assert calibra.acuracia_ocr("a educação", "a educacao") < 1.0


def test_le_o_gabarito(tmp_path):
    csv_path = tmp_path / "gabarito.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["arquivo", "nota_total", "c1", "c2", "c3", "c4", "c5", "tema"])
        escritor.writerow(["001.jpg", "760", "160", "160", "160", "120", "160", "Tema X"])

    itens = calibra.le_gabarito(csv_path)
    assert len(itens) == 1
    assert itens[0].arquivo == "001.jpg"
    assert itens[0].nota_total == 760
    assert itens[0].competencias == [160, 160, 160, 120, 160]
    assert itens[0].tema == "Tema X"


def test_gabarito_incoerente_e_rejeitado(tmp_path):
    """Se a soma das competências não bate com o total, o gabarito está errado."""
    csv_path = tmp_path / "gabarito.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["arquivo", "nota_total", "c1", "c2", "c3", "c4", "c5", "tema"])
        escritor.writerow(["001.jpg", "999", "160", "160", "160", "120", "160", "Tema X"])

    with pytest.raises(ValueError, match="não bate"):
        calibra.le_gabarito(csv_path)


def test_veredito_aprova_dentro_da_meta():
    assert calibra.veredito(erro_total=70, erro_competencia=35) == "APROVADO"


def test_veredito_reprova_erro_total_alto():
    assert calibra.veredito(erro_total=95, erro_competencia=35) == "REPROVADO"


def test_veredito_reprova_erro_por_competencia_alto():
    assert calibra.veredito(erro_total=70, erro_competencia=55) == "REPROVADO"
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/test_calibra.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'calibra'`.

- [ ] **Step 3: Escrever `calibra.py`**

```python
"""Métricas da calibração: quanto o corretor erra contra nota conhecida."""

from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Metas do spec. Passar nelas é a condição para o projeto continuar.
META_ERRO_TOTAL = 80
META_ERRO_COMPETENCIA = 40


@dataclass
class ItemGabarito:
    arquivo: str
    nota_total: int
    competencias: list
    tema: str


def le_gabarito(caminho: Path) -> list:
    """Lê o CSV de gabarito e valida a coerência de cada linha."""
    itens = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for numero, linha in enumerate(csv.DictReader(f), start=2):
            competencias = [int(linha[f"c{n}"]) for n in (1, 2, 3, 4, 5)]
            total = int(linha["nota_total"])
            if sum(competencias) != total:
                raise ValueError(
                    f"linha {numero} ({linha['arquivo']}): a soma das "
                    f"competências ({sum(competencias)}) não bate com a nota "
                    f"total ({total})"
                )
            itens.append(ItemGabarito(
                arquivo=linha["arquivo"],
                nota_total=total,
                competencias=competencias,
                tema=linha["tema"],
            ))
    return itens


def mae(pares) -> float:
    """Erro médio absoluto de uma lista de (oficial, previsto)."""
    if not pares:
        return 0.0
    return sum(abs(previsto - oficial) for oficial, previsto in pares) / len(pares)


def vies(pares) -> float:
    """Erro médio com sinal. Positivo = o corretor está sendo generoso."""
    if not pares:
        return 0.0
    return sum(previsto - oficial for oficial, previsto in pares) / len(pares)


def _tokens(texto: str) -> list:
    """Minúsculas e sem pontuação, mas COM acento — acento é erro de C1."""
    sem_pontuacao = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    return unicodedata.normalize("NFC", sem_pontuacao.lower()).split()


def acuracia_ocr(referencia: str, transcrito: str) -> float:
    """Semelhança palavra a palavra entre o texto digitado e o transcrito."""
    return difflib.SequenceMatcher(
        None, _tokens(referencia), _tokens(transcrito)
    ).ratio()


def veredito(erro_total: float, erro_competencia: float) -> str:
    dentro = erro_total <= META_ERRO_TOTAL and erro_competencia <= META_ERRO_COMPETENCIA
    return "APROVADO" if dentro else "REPROVADO"
```

- [ ] **Step 4: Rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/test_calibra.py -v
```

Esperado: 11 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/calibra.py projects/redacao-todo-dia/corretor/tests/test_calibra.py
git commit -m "feat(corretor): metricas de calibracao"
```

---

### Task 8: `run.py calibrar` — a porta de saída

**Files:**
- Modify: `projects/redacao-todo-dia/corretor/run.py`

- [ ] **Step 1: Montar o conjunto**

```
projects/redacao-todo-dia/corretor/dataset/
├── gabarito.csv
├── fotos/001.jpg, 002.jpg, ...
└── transcricoes/001.txt, ...   (opcional, para medir a leitura da letra)
```

`gabarito.csv` com cabeçalho `arquivo,nota_total,c1,c2,c3,c4,c5,tema`. Se a
soma das competências não bater com o total, o harness recusa a linha — é o
jeito de pegar erro de digitação antes de contaminar a métrica.

- [ ] **Step 2: Acrescentar o comando em `run.py`**

Antes de `main()`:

```python
def cmd_calibrar(args) -> None:
    import api
    import calibra

    base = Path(args.dataset)
    itens = calibra.le_gabarito(base / "gabarito.csv")
    cliente = cria_cliente()

    pares_total = []
    pares_competencia = []
    acuracias = []
    custo_total = 0.0
    falhas = []

    for indice, item in enumerate(itens, start=1):
        print(f"[{indice}/{len(itens)}] {item.arquivo}...", end=" ", flush=True)
        try:
            transcricao, uso_t = api.transcrever(cliente, base / "fotos" / item.arquivo)
            avaliacao, uso_a = api.avaliar(cliente, transcricao.texto, item.tema)
        except (api.FotoIlegivel, api.RecusaDaAPI) as erro:
            print(f"FALHOU ({erro})")
            falhas.append((item.arquivo, str(erro)))
            continue

        custo_total += api.custo_usd(uso_t) + api.custo_usd(uso_a)
        pares_total.append((item.nota_total, avaliacao["nota_total"]))
        for oficial, obtida in zip(item.competencias, avaliacao["competencias"]):
            pares_competencia.append((oficial, obtida["nota"]))

        referencia = base / "transcricoes" / f"{Path(item.arquivo).stem}.txt"
        if referencia.exists():
            acuracias.append(calibra.acuracia_ocr(
                referencia.read_text(encoding="utf-8"), transcricao.texto))

        diferenca = avaliacao["nota_total"] - item.nota_total
        print(f"oficial {item.nota_total} / obtida {avaliacao['nota_total']} "
              f"({diferenca:+d})")

    erro_total = calibra.mae(pares_total)
    erro_competencia = calibra.mae(pares_competencia)
    resultado = calibra.veredito(erro_total, erro_competencia)

    print("\n" + "=" * 52)
    print(f"redações avaliadas:        {len(pares_total)} de {len(itens)}")
    print(f"erro médio (nota total):   {erro_total:.1f}  (meta ≤ {calibra.META_ERRO_TOTAL})")
    print(f"erro médio (competência):  {erro_competencia:.1f}  (meta ≤ {calibra.META_ERRO_COMPETENCIA})")
    print(f"viés:                      {calibra.vies(pares_total):+.1f}"
          f"  ({'generoso' if calibra.vies(pares_total) > 0 else 'duro'})")
    if acuracias:
        media_ocr = sum(acuracias) / len(acuracias)
        print(f"leitura da letra:          {media_ocr:.1%}  (meta ≥ 90%)")
    print(f"custo total:               US$ {custo_total:.2f}")
    print(f"custo por correção:        US$ {custo_total / max(len(pares_total), 1):.4f}")
    if falhas:
        print(f"\nfalhas ({len(falhas)}):")
        for arquivo, erro in falhas:
            print(f"  {arquivo}: {erro}")
    print("=" * 52)
    print(f"\n{resultado}")
```

E dentro de `main()`:

```python
    p_calibrar = sub.add_parser("calibrar", help="roda o conjunto de calibração")
    p_calibrar.add_argument("--dataset", default="dataset",
                            help="pasta do conjunto (padrão: dataset)")
    p_calibrar.set_defaults(func=cmd_calibrar)
```

- [ ] **Step 3: Rodar a calibração**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff/projects/redacao-todo-dia/corretor"
python3 run.py calibrar
```

Custo esperado: ~US$ 1,60 para 20 redações. Saída:

```
[1/20] 001.jpg... oficial 760 / obtida 720 (-40)
...
====================================================
redações avaliadas:        20 de 20
erro médio (nota total):   62.0  (meta ≤ 80)
erro médio (competência):  31.0  (meta ≤ 40)
viés:                      -18.0  (duro)
leitura da letra:          94.2%  (meta ≥ 90%)
custo total:               US$ 1.63
custo por correção:        US$ 0.0815
====================================================

APROVADO
```

- [ ] **Step 4: A decisão**

| Resultado | O que fazer |
|---|---|
| **APROVADO** e leitura ≥ 90% | Segue para o plano do app. Registre os números no spec |
| **REPROVADO** com viés forte (acima de ±60) | O modelo é consistente, só descalibrado. Ajuste as âncoras de nota na `RUBRICA` e rode de novo. Vale até 3 tentativas |
| **REPROVADO** com viés perto de zero e erro alto | O modelo está errando para os dois lados — é inconsistência, não calibração. Prompt não resolve. **Mata o projeto** |
| Leitura da letra < 90% | Antes de mexer na rubrica, teste fotos melhores. Se persistir com foto boa, a etapa de confirmação precisa virar edição de texto no app — e isso muda o plano do app |

O terceiro caso é o que este plano existe para descobrir. Se cair nele, o custo
foi uma semana, e não uma semana mais um app, uma landing e 60 temas.

- [ ] **Step 5: Commit e registro**

```bash
cd "/Users/sergiogpngmail.com/Chief of Staff"
git add projects/redacao-todo-dia/corretor/run.py
git commit -m "feat(corretor): comando calibrar com veredito contra a meta"
```

Depois acrescente ao spec, na seção "Testes", uma linha com a data, os números
obtidos e o veredito. Esse registro é o que justifica a decisão de seguir ou
parar quando você olhar isso daqui a três semanas.

---

## Cobertura do spec

| Requisito do spec | Onde | Observação |
|---|---|---|
| Transcrição separada da avaliação | Tarefas 4 e 6 | Confirmação humana no meio |
| Saída estruturada nas 5 competências | Tarefa 5 | `output_config.format` |
| Regras de anulação do ENEM | Tarefa 2 | Corrigidas: fuga total anula tudo |
| Cache da rubrica | Tarefa 5 | Testado no cliente falso |
| Custo por correção medido | Tarefas 5, 6, 8 | Impresso ao fim de cada correção |
| Teto de 3 correções/dia | — | É do app, não do harness |
| Calibração ≤ 80 pts / ≤ 40 por competência | Tarefas 7 e 8 | O critério de vida ou morte |
| Precisão da leitura ≥ 90% | Tarefas 7 e 8 | Só roda se houver transcrição de referência |
| Detecção de fuga ao tema | Tarefas 2 e 3 | Fuga vs. tangenciamento separados |
| Foto ilegível não consome cota | Tarefas 4 e 8 | `FotoIlegivel` entra como falha, não como nota |

**Fora deste plano** (vão para o plano do app, se houver): webhook da Kiwify,
magic link, painel de evolução, desafio diário, os 60 temas, landing, e o
retry com backoff em falha de API.

---
**See also:** [[Redação Todo Dia]] | [[Atendente IA]]
