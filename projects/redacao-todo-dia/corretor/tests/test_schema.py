"""Testes das regras de nota do ENEM — a parte que não pode errar.

Regras conferidas contra a Cartilha do Participante do INEP.
"""

import pytest

import schema


def avaliacao(notas=(160, 160, 160, 160, 160), linhas=25, enquadramento="ok",
              linhas_copiadas=0, fere_direitos_humanos=False):
    """Monta uma avaliação crua, como o modelo devolveria."""
    return {
        "competencias": [
            {"numero": n, "nota": nota, "justificativa": "...", "melhorias": ["a", "b"]}
            for n, nota in enumerate(notas, start=1)
        ],
        "linhas": linhas,
        "linhas_copiadas": linhas_copiadas,
        "enquadramento": enquadramento,
        "fere_direitos_humanos": fere_direitos_humanos,
        "resumo": "...",
    }


def notas_de(resultado):
    return [c["nota"] for c in resultado["competencias"]]


# --- soma e caso normal --------------------------------------------------

def test_soma_as_cinco_competencias():
    resultado = schema.normaliza(avaliacao(notas=(200, 160, 120, 80, 40)))
    assert resultado["nota_total"] == 600
    assert resultado["penalidades"] == []
    assert resultado["anulada"] is False


def test_competencias_saem_ordenadas():
    crua = avaliacao()
    crua["competencias"].reverse()
    resultado = schema.normaliza(crua)
    assert [c["numero"] for c in resultado["competencias"]] == [1, 2, 3, 4, 5]


def test_nota_total_nunca_passa_de_mil():
    resultado = schema.normaliza(avaliacao(notas=(200, 200, 200, 200, 200)))
    assert resultado["nota_total"] == 1000


# --- contagem de linhas --------------------------------------------------

def test_ate_sete_linhas_anula():
    resultado = schema.normaliza(avaliacao(linhas=7))
    assert resultado["nota_total"] == 0
    assert notas_de(resultado) == [0, 0, 0, 0, 0]
    assert any("insuficiente" in p for p in resultado["penalidades"])


def test_oito_linhas_nao_anula():
    resultado = schema.normaliza(avaliacao(linhas=8))
    assert resultado["nota_total"] == 800
    assert resultado["penalidades"] == []


# --- cópia dos textos motivadores ---------------------------------------

def test_copia_desconta_linhas_mas_nao_anula():
    """Cópia não zera: desconta as linhas copiadas da contagem."""
    resultado = schema.normaliza(avaliacao(linhas=28, linhas_copiadas=3))
    assert resultado["linhas_validas"] == 25
    assert resultado["nota_total"] == 800
    assert resultado["penalidades"] == []


def test_copia_anula_quando_derruba_abaixo_do_minimo():
    resultado = schema.normaliza(avaliacao(linhas=25, linhas_copiadas=20))
    assert resultado["linhas_validas"] == 5
    assert resultado["nota_total"] == 0
    assert any("insuficiente" in p for p in resultado["penalidades"])


def test_recusa_mais_linhas_copiadas_do_que_escritas():
    with pytest.raises(ValueError, match="linhas_copiadas"):
        schema.normaliza(avaliacao(linhas=10, linhas_copiadas=11))


# --- causas de anulação --------------------------------------------------

@pytest.mark.parametrize("enquadramento", sorted(schema.ANULA))
def test_cada_causa_de_anulacao_zera_tudo(enquadramento):
    resultado = schema.normaliza(avaliacao(enquadramento=enquadramento))
    assert resultado["nota_total"] == 0
    assert notas_de(resultado) == [0, 0, 0, 0, 0]
    assert resultado["anulada"] is True


def test_lista_de_anulacao_cobre_a_cartilha():
    esperado = {
        "fuga_total", "nao_dissertativo", "parte_desconectada", "improperios",
        "identificacao", "lingua_estrangeira", "ilegivel", "em_branco",
    }
    assert set(schema.ANULA) == esperado


def test_duas_causas_simultaneas_aparecem_juntas():
    resultado = schema.normaliza(avaliacao(linhas=3, enquadramento="fuga_total"))
    assert len(resultado["penalidades"]) == 2


# --- tangenciamento ------------------------------------------------------

def test_tangenciamento_nao_anula():
    resultado = schema.normaliza(avaliacao(enquadramento="tangenciamento"))
    assert resultado["anulada"] is False


def test_tangenciamento_limita_c2_c3_e_c5_em_quarenta():
    """Regra da cartilha: tangenciar trava C2, C3 e C5 em no máximo 40."""
    resultado = schema.normaliza(
        avaliacao(notas=(200, 200, 200, 200, 200), enquadramento="tangenciamento"))
    assert notas_de(resultado) == [200, 40, 40, 200, 40]
    assert resultado["nota_total"] == 520


def test_tangenciamento_nao_sobe_nota_que_ja_era_baixa():
    resultado = schema.normaliza(
        avaliacao(notas=(160, 0, 40, 160, 0), enquadramento="tangenciamento"))
    assert notas_de(resultado) == [160, 0, 40, 160, 0]


# --- direitos humanos ----------------------------------------------------

def test_desrespeito_aos_direitos_humanos_zera_so_a_c5():
    resultado = schema.normaliza(avaliacao(fere_direitos_humanos=True))
    assert notas_de(resultado) == [160, 160, 160, 160, 0]
    assert resultado["nota_total"] == 640


def test_direitos_humanos_e_tangenciamento_convivem():
    resultado = schema.normaliza(
        avaliacao(notas=(200, 200, 200, 200, 200),
                  enquadramento="tangenciamento", fere_direitos_humanos=True))
    assert notas_de(resultado) == [200, 40, 40, 200, 0]


# --- validação: falha fechada -------------------------------------------

def test_enquadramento_desconhecido_e_recusado():
    """Fail-closed: não pode virar 'sem penalidade' em silêncio."""
    with pytest.raises(ValueError, match="enquadramento"):
        schema.normaliza(avaliacao(enquadramento="fuga"))


def test_nota_fora_do_grid_e_recusada():
    with pytest.raises(ValueError, match="grid"):
        schema.normaliza(avaliacao(notas=(150, 160, 160, 160, 160)))


def test_nota_acima_do_maximo_e_recusada():
    with pytest.raises(ValueError, match="grid"):
        schema.normaliza(avaliacao(notas=(999, 160, 160, 160, 160)))


def test_nota_como_texto_e_recusada():
    with pytest.raises(ValueError, match="grid"):
        schema.normaliza(avaliacao(notas=("160", 160, 160, 160, 160)))


def test_linhas_negativo_e_recusado():
    """Zero falso é pior que erro: 'até 7 linhas' numa redação de 25 é mentira."""
    with pytest.raises(ValueError, match="linhas"):
        schema.normaliza(avaliacao(linhas=-3))


def test_linhas_como_texto_e_recusado():
    with pytest.raises(ValueError, match="linhas"):
        schema.normaliza(avaliacao(linhas="25"))


def test_recusa_avaliacao_sem_as_cinco_competencias():
    crua = avaliacao()
    crua["competencias"] = crua["competencias"][:4]
    with pytest.raises(ValueError, match="5 competências"):
        schema.normaliza(crua)


def test_recusa_competencia_repetida():
    crua = avaliacao()
    crua["competencias"][4]["numero"] = 1
    with pytest.raises(ValueError, match="repetida"):
        schema.normaliza(crua)


# --- não mutar a entrada -------------------------------------------------

def test_nao_muta_a_avaliacao_recebida():
    crua = avaliacao(enquadramento="fuga_total")
    schema.normaliza(crua)
    assert [c["nota"] for c in crua["competencias"]] == [160] * 5


def test_nao_compartilha_listas_com_a_entrada():
    crua = avaliacao()
    resultado = schema.normaliza(crua)
    resultado["competencias"][0]["melhorias"].append("X")
    assert crua["competencias"][0]["melhorias"] == ["a", "b"]


# --- schema --------------------------------------------------------------

def test_schema_nao_usa_recursos_nao_suportados():
    """A API rejeita minimum/maximum/minLength — o grid de notas vira enum."""
    texto = repr(schema.AVALIACAO_SCHEMA)
    for proibido in ("minimum", "maximum", "minLength", "maxLength",
                     "multipleOf", "minItems", "maxItems", "pattern"):
        assert proibido not in texto


def test_schema_fecha_objetos_em_todos_os_niveis():
    assert schema.AVALIACAO_SCHEMA["additionalProperties"] is False
    item = schema.AVALIACAO_SCHEMA["properties"]["competencias"]["items"]
    assert item["additionalProperties"] is False


def test_schema_nao_pede_nota_total_ao_modelo():
    """Somar é nosso. Se o modelo somasse, teria como errar."""
    assert "nota_total" not in schema.AVALIACAO_SCHEMA["properties"]


def test_schema_pede_tudo_que_o_modelo_pode_julgar():
    exigido = set(schema.AVALIACAO_SCHEMA["required"])
    assert {"competencias", "enquadramento", "fere_direitos_humanos",
            "resumo"} <= exigido


def test_schema_nao_pede_contagem_de_linhas_ao_modelo():
    """O avaliador não vê a foto — quem conta linhas é a transcrição."""
    assert "linhas" not in schema.AVALIACAO_SCHEMA["properties"]
    assert "linhas_copiadas" not in schema.AVALIACAO_SCHEMA["properties"]


def test_enum_do_schema_nao_e_o_mesmo_objeto_das_constantes():
    """Evita que um append numa constante reescreva o schema em silêncio."""
    enum_notas = schema.AVALIACAO_SCHEMA["properties"]["competencias"]["items"] \
        ["properties"]["nota"]["enum"]
    assert enum_notas is not schema.NOTAS_VALIDAS


def test_avaliacao_sem_linhas_e_recusada():
    """Falha alto: sem linhas, o default 0 anularia tudo em silêncio."""
    crua = avaliacao()
    del crua["linhas"]
    with pytest.raises(ValueError, match="linhas"):
        schema.normaliza(crua)
