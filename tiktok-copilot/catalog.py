"""Catalogo de produtos.

v1 le de um JSON local que o vendedor edita (ou que o painel escreve). A API
oficial do TikTok Shop exige aprovacao de partner app, que leva semanas -- por
isso ela nao esta no caminho critico. Quando sair, basta implementar outro
loader com a mesma assinatura de `load()`.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "products.json"


def load(path: Path | str = DEFAULT_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("produtos", []) if isinstance(data, dict) else data


def as_prompt_block(produtos: list[dict], frete: dict | None = None) -> str:
    """Serializa o catalogo para dentro do system prompt.

    Formato de linha unica por produto: barato em tokens e facil do modelo
    citar de volta sem alucinar campo.
    """
    if not produtos:
        return "CATALOGO: vazio (nenhum produto cadastrado)."

    linhas = []
    for p in produtos:
        preco = p.get("preco")
        preco_txt = f"R${preco:.2f}".replace(".", ",") if isinstance(preco, (int, float)) else "-"
        estoque = p.get("estoque")
        estoque_txt = "esgotado" if estoque == 0 else (f"{estoque} un" if estoque else "disponivel")
        partes = [
            f"- {p.get('nome', 'sem nome')}",
            f"preco {preco_txt}",
            f"estoque {estoque_txt}",
        ]
        if p.get("tamanhos"):
            partes.append("tamanhos " + "/".join(str(t) for t in p["tamanhos"]))
        if p.get("cores"):
            partes.append("cores " + "/".join(str(c) for c in p["cores"]))
        if p.get("obs"):
            partes.append(str(p["obs"]))
        linhas.append(" | ".join(partes))

    bloco = "CATALOGO:\n" + "\n".join(linhas)

    if frete:
        regras = "\n".join(f"- {k}: {v}" for k, v in frete.items())
        bloco += f"\n\nFRETE E PRAZO:\n{regras}"

    return bloco


def load_frete(path: Path | str = DEFAULT_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("frete", {}) if isinstance(data, dict) else {}
