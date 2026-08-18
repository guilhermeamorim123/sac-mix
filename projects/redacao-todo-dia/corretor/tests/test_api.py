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


def test_transcrever_recusa_texto_sem_cabecalho_de_linhas(tmp_path):
    """Contar parágrafos como linhas produziria anulação falsa."""
    cliente = FakeClient(resposta("primeira linha\nsegunda linha"))
    with pytest.raises(api.TranscricaoSemContagem):
        api.transcrever(cliente, foto_falsa(tmp_path))


# --- avaliar -------------------------------------------------------------

import json

import prompts
import schema


def avaliacao_json(nota=160, enquadramento="ok", fere_direitos_humanos=False):
    return json.dumps({
        "competencias": [
            {"numero": n, "nota": nota, "justificativa": "j", "melhorias": ["a", "b"]}
            for n in (1, 2, 3, 4, 5)
        ],
        "enquadramento": enquadramento,
        "fere_direitos_humanos": fere_direitos_humanos,
        "resumo": "r",
    })


def test_avaliar_devolve_avaliacao_normalizada():
    cliente = FakeClient(resposta(avaliacao_json(nota=160)))
    resultado, _ = api.avaliar(cliente, "texto da redação", "Tema qualquer", linhas=25)
    assert resultado["nota_total"] == 800
    assert resultado["penalidades"] == []


def test_avaliar_aplica_as_regras_de_anulacao():
    cliente = FakeClient(resposta(avaliacao_json(nota=200, enquadramento="fuga_total")))
    resultado, _ = api.avaliar(cliente, "texto", "Tema", linhas=25)
    assert resultado["nota_total"] == 0
    assert resultado["anulada"] is True


def test_avaliar_aplica_o_teto_do_tangenciamento():
    cliente = FakeClient(resposta(avaliacao_json(nota=200, enquadramento="tangenciamento")))
    resultado, _ = api.avaliar(cliente, "texto", "Tema", linhas=25)
    assert [c["nota"] for c in resultado["competencias"]] == [200, 40, 40, 200, 40]


def test_avaliar_exige_saida_estruturada():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto", "Tema", linhas=25)
    enviado = cliente.messages.chamada
    assert enviado["output_config"]["format"]["type"] == "json_schema"
    assert enviado["output_config"]["format"]["schema"] == schema.AVALIACAO_SCHEMA


def test_avaliar_cacheia_a_rubrica():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto", "Tema", linhas=25)
    bloco_sistema = cliente.messages.chamada["system"][0]
    assert bloco_sistema["text"] == prompts.RUBRICA
    assert bloco_sistema["cache_control"] == {"type": "ephemeral"}


def test_avaliar_manda_o_tema_junto():
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto da redação", "Desafios da mobilidade urbana", linhas=25)
    conteudo = cliente.messages.chamada["messages"][0]["content"]
    assert "Desafios da mobilidade urbana" in conteudo
    assert "texto da redação" in conteudo


def test_avaliar_levanta_erro_em_recusa():
    cliente = FakeClient(resposta("", stop_reason="refusal"))
    with pytest.raises(api.RecusaDaAPI):
        api.avaliar(cliente, "texto", "Tema", linhas=25)


def test_avaliar_injeta_as_linhas_da_transcricao():
    """O avaliador não vê a foto; quem conta linhas é a etapa anterior."""
    cliente = FakeClient(resposta(avaliacao_json(nota=160)))
    resultado, _ = api.avaliar(cliente, "texto", "Tema", linhas=25)
    assert resultado["linhas"] == 25
    assert resultado["nota_total"] == 800


def test_avaliar_com_poucas_linhas_anula_pelo_numero_da_transcricao():
    cliente = FakeClient(resposta(avaliacao_json(nota=200)))
    resultado, _ = api.avaliar(cliente, "texto", "Tema", linhas=5)
    assert resultado["nota_total"] == 0


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


# --- resposta sem texto --------------------------------------------------

def test_resposta_sem_bloco_de_texto_da_erro_claro():
    """No Opus 5 o thinking vem ligado; se max_tokens cortar, não sobra texto."""
    vazia = SimpleNamespace(
        stop_reason="max_tokens", stop_details=None, model="claude-opus-5",
        content=[SimpleNamespace(type="thinking", thinking="...")], usage=uso(),
    )
    with pytest.raises(api.RespostaSemTexto, match="max_tokens"):
        api._texto_da_resposta(vazia)


def test_resposta_com_content_vazio_da_erro_claro():
    vazia = SimpleNamespace(
        stop_reason="end_turn", stop_details=None, model="claude-opus-5",
        content=[], usage=uso(),
    )
    with pytest.raises(api.RespostaSemTexto):
        api._texto_da_resposta(vazia)


# --- effort por etapa -----------------------------------------------------

def test_transcrever_usa_effort_baixo(tmp_path):
    """OCR não precisa de raciocínio profundo — é a alavanca de custo."""
    cliente = FakeClient(resposta("LINHAS: 10\n\ntexto"))
    api.transcrever(cliente, foto_falsa(tmp_path))
    assert cliente.messages.chamada["output_config"]["effort"] == "low"


def test_avaliar_usa_o_effort_configurado(tmp_path):
    cliente = FakeClient(resposta(avaliacao_json()))
    api.avaliar(cliente, "texto", "Tema", linhas=25)
    assert cliente.messages.chamada["output_config"]["effort"] == api.EFFORT_AVALIACAO
