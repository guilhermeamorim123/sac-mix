"""Catalogo: produtos, frete e base de conhecimento.

Duas origens, mesma forma final:

- **banco** (`STORE_BACKEND=supabase`) -- o lojista edita pelo painel, nas abas
  Produtos / Frete / Base de Conhecimento das Configuracoes. Esta e a origem de
  verdade no uso normal.
- **products.json** -- arquivo local, usado no modo sqlite e como fallback
  offline. Bom para testar sem subir nada.

A API oficial do TikTok Shop exige aprovacao de partner app (semanas), por isso
ela nao esta no caminho critico. Quando sair, vira um terceiro `from_*`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "products.json"


def _num(valor) -> float | None:
    """Numeric do Postgres pode chegar como float ou string, dependendo do driver."""
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _lista(valor) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, str):
        return [valor]
    return [str(v) for v in valor if v]


@dataclass(frozen=True)
class Catalog:
    """O que a IA sabe sobre a loja. Tudo que ela pode citar sem alucinar."""

    produtos: list[dict] = field(default_factory=list)
    frete: dict[str, str] = field(default_factory=dict)
    conhecimento: list[dict] = field(default_factory=list)
    origem: str = "json"

    # ------------------------------------------------------------------
    # construtores
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: Path | str = DEFAULT_PATH) -> "Catalog":
        path = Path(path)
        if not path.exists():
            return cls(origem="json (arquivo ausente)")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return cls(produtos=list(data), origem="json")
        return cls(
            produtos=data.get("produtos", []),
            frete=data.get("frete", {}),
            conhecimento=data.get("conhecimento", []),
            origem="json",
        )

    @classmethod
    def from_rows(
        cls,
        produtos: list[dict],
        frete: list[dict],
        conhecimento: list[dict] | None = None,
    ) -> "Catalog":
        """Monta a partir das linhas das tabelas `produtos`, `frete_regras` e
        `base_conhecimento`. Ja chega ordenado por `ordem` do banco."""
        return cls(
            produtos=[
                {
                    "nome": p.get("nome", "sem nome"),
                    "preco": _num(p.get("preco")),
                    "estoque": p.get("estoque"),
                    "cores": _lista(p.get("cores")),
                    "tamanhos": _lista(p.get("tamanhos")),
                    "obs": p.get("obs"),
                }
                for p in produtos
            ],
            frete={f["regiao"]: f["descricao"] for f in frete if f.get("regiao")},
            conhecimento=[
                {"titulo": c.get("titulo", ""), "conteudo": c.get("conteudo", "")}
                for c in (conhecimento or [])
            ],
            origem="banco",
        )

    # ------------------------------------------------------------------
    # uso
    # ------------------------------------------------------------------

    @property
    def fingerprint(self) -> str:
        """Hash do conteudo. O agente compara a cada refresh para saber se o
        lojista mexeu no catalogo durante a live -- so ai vale reconstruir o
        prompt (e pagar cache-miss)."""
        bruto = json.dumps(
            [self.produtos, self.frete, self.conhecimento],
            sort_keys=True, ensure_ascii=False, default=str,
        )
        return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]

    @property
    def vazio(self) -> bool:
        return not self.produtos

    def as_prompt_block(self) -> str:
        """Serializa para dentro do system prompt.

        Uma linha por produto: barato em tokens e facil do modelo citar de volta
        sem inventar campo.
        """
        if not self.produtos:
            bloco = "CATALOGO: vazio (nenhum produto cadastrado)."
        else:
            linhas = []
            for p in self.produtos:
                preco = p.get("preco")
                preco_txt = (
                    f"R${preco:.2f}".replace(".", ",")
                    if isinstance(preco, (int, float)) else "-"
                )
                estoque = p.get("estoque")
                estoque_txt = (
                    "esgotado" if estoque == 0
                    else (f"{estoque} un" if estoque else "disponivel")
                )
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

        if self.frete:
            regras = "\n".join(f"- {k}: {v}" for k, v in self.frete.items())
            bloco += f"\n\nFRETE E PRAZO:\n{regras}"

        if self.conhecimento:
            artigos = "\n".join(
                f"- {c['titulo']}: {c['conteudo']}"
                for c in self.conhecimento if c.get("conteudo")
            )
            if artigos:
                bloco += f"\n\nBASE DE CONHECIMENTO DA LOJA:\n{artigos}"

        return bloco
