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
