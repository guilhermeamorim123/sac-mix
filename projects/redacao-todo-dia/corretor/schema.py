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
