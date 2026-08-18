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
