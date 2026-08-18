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


def escreve_gabarito(tmp_path, *linhas):
    caminho = tmp_path / "gabarito.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["arquivo", "nota_total", "c1", "c2", "c3", "c4", "c5", "tema"])
        for linha in linhas:
            escritor.writerow(linha)
    return caminho


def test_le_o_gabarito(tmp_path):
    caminho = escreve_gabarito(
        tmp_path, ["001.jpg", "760", "160", "160", "160", "120", "160", "Tema X"])
    itens = calibra.le_gabarito(caminho)
    assert len(itens) == 1
    assert itens[0].arquivo == "001.jpg"
    assert itens[0].nota_total == 760
    assert itens[0].competencias == [160, 160, 160, 120, 160]
    assert itens[0].tema == "Tema X"


def test_gabarito_incoerente_e_rejeitado(tmp_path):
    """Se a soma das competências não bate com o total, o gabarito está errado."""
    caminho = escreve_gabarito(
        tmp_path, ["001.jpg", "999", "160", "160", "160", "120", "160", "Tema X"])
    with pytest.raises(ValueError, match="não bate"):
        calibra.le_gabarito(caminho)


def test_gabarito_com_nota_fora_do_grid_e_rejeitado(tmp_path):
    caminho = escreve_gabarito(
        tmp_path, ["001.jpg", "750", "150", "160", "160", "120", "160", "Tema X"])
    with pytest.raises(ValueError, match="grid"):
        calibra.le_gabarito(caminho)


def test_veredito_aprova_dentro_da_meta():
    assert calibra.veredito(erro_total=70, erro_competencia=35) == "APROVADO"


def test_veredito_reprova_erro_total_alto():
    assert calibra.veredito(erro_total=95, erro_competencia=35) == "REPROVADO"


def test_veredito_reprova_erro_por_competencia_alto():
    assert calibra.veredito(erro_total=70, erro_competencia=55) == "REPROVADO"
