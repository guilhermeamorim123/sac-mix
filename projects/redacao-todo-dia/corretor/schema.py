"""Contrato da avaliação e as regras de nota do ENEM.

O modelo julga cada competência. Toda regra determinística fica aqui —
somar, aplicar tetos e anular — porque é onde LLM erra sem ganhar nada em
troca.

Regras conferidas contra a Cartilha do Participante do INEP:
https://download.inep.gov.br/publicacoes/institucionais/avaliacoes_e_exames_da_educacao_basica/a_redacao_no_enem_2025_cartilha_do_participante.pdf
"""

from __future__ import annotations

import copy

COMPETENCIAS = {
    1: "Domínio da modalidade escrita formal da língua portuguesa",
    2: "Compreender a proposta e aplicar conceitos de várias áreas do conhecimento",
    3: "Selecionar, relacionar, organizar e interpretar informações em defesa de um ponto de vista",
    4: "Conhecimento dos mecanismos linguísticos de construção da argumentação",
    5: "Elaborar proposta de intervenção que respeite os direitos humanos",
}

# O ENEM só dá nota em múltiplos de 40, de 0 a 200, por competência.
NOTAS_VALIDAS = (0, 40, 80, 120, 160, 200)

# Causas de nota zero na redação inteira, conforme a cartilha.
# Tangenciamento NÃO está aqui — tem tratamento próprio, ver TETO_TANGENCIAMENTO.
# Cópia dos textos motivadores também NÃO está aqui — desconta linhas, não anula.
ANULA = {
    "fuga_total": "fuga total ao tema",
    "nao_dissertativo": "não obediência ao tipo dissertativo-argumentativo",
    "parte_desconectada": "parte deliberadamente desconectada do tema",
    "improperios": "impropérios, desenhos ou outra forma proposital de anulação",
    "identificacao": "identificação fora do espaço destinado",
    "lingua_estrangeira": "texto predominantemente em língua estrangeira",
    "ilegivel": "texto ilegível",
    "em_branco": "folha em branco",
}

ENQUADRAMENTOS = ("ok", "tangenciamento", *ANULA)

# Tangenciar o tema trava C2, C3 e C5 em no máximo 40 pontos cada.
TETO_TANGENCIAMENTO = 40
COMPETENCIAS_TANGENCIADAS = (2, 3, 5)

# "Extensão de até 7 linhas manuscritas" anula; a partir de 8 vale.
LINHAS_MINIMAS = 8

AVALIACAO_SCHEMA = {
    "type": "object",
    "properties": {
        "competencias": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                    "nota": {"type": "integer", "enum": list(NOTAS_VALIDAS)},
                    "justificativa": {"type": "string"},
                    "melhorias": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["numero", "nota", "justificativa", "melhorias"],
                "additionalProperties": False,
            },
        },
        "linhas": {"type": "integer"},
        "linhas_copiadas": {"type": "integer"},
        "enquadramento": {"type": "string", "enum": list(ENQUADRAMENTOS)},
        "fere_direitos_humanos": {"type": "boolean"},
        "resumo": {"type": "string"},
    },
    "required": ["competencias", "linhas", "linhas_copiadas", "enquadramento",
                 "fere_direitos_humanos", "resumo"],
    "additionalProperties": False,
}


def _valida_competencias(avaliacao: dict) -> dict:
    itens = avaliacao["competencias"]
    por_numero = {}
    for item in itens:
        numero = item["numero"]
        if numero in por_numero:
            raise ValueError(f"competência {numero} veio repetida")
        if type(item["nota"]) is not int or item["nota"] not in NOTAS_VALIDAS:
            raise ValueError(
                f"competência {numero}: nota {item['nota']!r} fora do grid "
                f"{list(NOTAS_VALIDAS)}"
            )
        por_numero[numero] = copy.deepcopy(item)
    if sorted(por_numero) != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"esperava as 5 competências, vieram {sorted(por_numero)}"
        )
    return por_numero


def _valida_contagem(avaliacao: dict, chave: str) -> int:
    valor = avaliacao.get(chave, 0)
    if type(valor) is not int or valor < 0:
        raise ValueError(f"{chave} deve ser inteiro não-negativo, veio {valor!r}")
    return valor


def normaliza(avaliacao: dict) -> dict:
    """Aplica as regras do ENEM e calcula a nota total.

    Devolve um dicionário novo com `nota_total`, `linhas_validas`,
    `penalidades` (lista, vazia quando nada foi anulado) e `anulada`.
    Levanta ValueError em qualquer entrada que não faça sentido — falhar alto
    é melhor que produzir nota errada com aparência de certa.
    """
    competencias = _valida_competencias(avaliacao)

    enquadramento = avaliacao["enquadramento"]
    if enquadramento not in ENQUADRAMENTOS:
        raise ValueError(
            f"enquadramento desconhecido: {enquadramento!r}. "
            f"Esperado um de {list(ENQUADRAMENTOS)}"
        )

    linhas = _valida_contagem(avaliacao, "linhas")
    copiadas = _valida_contagem(avaliacao, "linhas_copiadas")
    if copiadas > linhas:
        raise ValueError(
            f"linhas_copiadas ({copiadas}) é maior que linhas ({linhas})"
        )
    linhas_validas = linhas - copiadas

    penalidades = []
    if enquadramento in ANULA:
        penalidades.append(ANULA[enquadramento])
    if linhas_validas < LINHAS_MINIMAS:
        penalidades.append(
            f"texto insuficiente: {linhas_validas} linha(s) válida(s), "
            f"o mínimo é {LINHAS_MINIMAS}"
        )

    if penalidades:
        for numero in competencias:
            competencias[numero]["nota"] = 0
    else:
        if enquadramento == "tangenciamento":
            for numero in COMPETENCIAS_TANGENCIADAS:
                competencias[numero]["nota"] = min(
                    competencias[numero]["nota"], TETO_TANGENCIAMENTO
                )
        if avaliacao.get("fere_direitos_humanos"):
            competencias[5]["nota"] = 0

    resultado = copy.deepcopy(avaliacao)
    resultado.update({
        "competencias": [competencias[n] for n in (1, 2, 3, 4, 5)],
        "linhas_validas": linhas_validas,
        "nota_total": sum(c["nota"] for c in competencias.values()),
        "penalidades": penalidades,
        "anulada": bool(penalidades),
    })
    return resultado
