"""Testes dos prompts — estruturais, garantem que a rubrica e o schema batem."""

import prompts
import schema


def test_rubrica_cobre_as_cinco_competencias():
    for numero in (1, 2, 3, 4, 5):
        assert f"Competência {numero}" in prompts.RUBRICA


def test_rubrica_ensina_todos_os_enquadramentos_do_schema():
    """O modelo só pode devolver valor que o schema aceita — e vice-versa."""
    for valor in schema.ENQUADRAMENTOS:
        assert f"`{valor}`" in prompts.RUBRICA, f"faltou ensinar {valor}"


def test_rubrica_separa_fuga_total_de_tangenciamento():
    assert "tangenciamento" in prompts.RUBRICA.lower()
    assert "fuga total" in prompts.RUBRICA.lower()


def test_rubrica_pede_as_linhas_copiadas():
    assert "linhas_copiadas" in prompts.RUBRICA


def test_rubrica_pede_o_juizo_de_direitos_humanos():
    assert "fere_direitos_humanos" in prompts.RUBRICA


def test_rubrica_proibe_o_modelo_de_somar():
    assert "não some" in prompts.RUBRICA.lower()


def test_rubrica_proibe_o_modelo_de_anular():
    assert "não aplique" in prompts.RUBRICA.lower()


def test_rubrica_e_grande_o_bastante_para_cachear():
    """O mínimo cacheável no Opus 5 é 512 tokens (~2000 caracteres)."""
    assert len(prompts.RUBRICA) > 2500


def test_prompt_de_transcricao_proibe_avaliar():
    assert "não avalie" in prompts.TRANSCRICAO.lower()


def test_prompt_de_transcricao_pede_fidelidade_aos_erros():
    assert "não corrija" in prompts.TRANSCRICAO.lower()


def test_prompt_de_transcricao_define_o_sinal_de_foto_ilegivel():
    assert "FOTO_ILEGIVEL" in prompts.TRANSCRICAO
