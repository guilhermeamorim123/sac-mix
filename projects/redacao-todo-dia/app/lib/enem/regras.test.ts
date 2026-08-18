/**
 * Os mesmos testes de `corretor/tests/test_schema.py`, portados.
 *
 * O ponto de portar os testes junto é que o porte de Python para TypeScript
 * não pode introduzir divergência na única lógica que decide a nota do aluno.
 */

import { describe, expect, it } from "vitest";

import {
  ANULA,
  AVALIACAO_SCHEMA,
  AvaliacaoInvalida,
  NOTAS_VALIDAS,
  normaliza,
  type AvaliacaoCrua,
} from "./regras";

function avaliacao(over: Partial<AvaliacaoCrua> & { notas?: number[] } = {}): AvaliacaoCrua {
  const notas = over.notas ?? [160, 160, 160, 160, 160];
  return {
    competencias: notas.map((nota, i) => ({
      numero: i + 1,
      nota,
      justificativa: "...",
      melhorias: ["a", "b"],
    })),
    linhas: over.linhas ?? 25,
    linhas_copiadas: over.linhas_copiadas ?? 0,
    enquadramento: over.enquadramento ?? "ok",
    fere_direitos_humanos: over.fere_direitos_humanos ?? false,
    resumo: "...",
  };
}

const notasDe = (r: { competencias: { nota: number }[] }) => r.competencias.map((c) => c.nota);

describe("soma e caso normal", () => {
  it("soma as cinco competências", () => {
    const r = normaliza(avaliacao({ notas: [200, 160, 120, 80, 40] }));
    expect(r.nota_total).toBe(600);
    expect(r.penalidades).toEqual([]);
    expect(r.anulada).toBe(false);
  });

  it("devolve as competências ordenadas", () => {
    const crua = avaliacao();
    crua.competencias.reverse();
    expect(normaliza(crua).competencias.map((c) => c.numero)).toEqual([1, 2, 3, 4, 5]);
  });

  it("nunca passa de mil", () => {
    expect(normaliza(avaliacao({ notas: [200, 200, 200, 200, 200] })).nota_total).toBe(1000);
  });
});

describe("contagem de linhas", () => {
  it("até sete linhas anula", () => {
    const r = normaliza(avaliacao({ linhas: 7 }));
    expect(r.nota_total).toBe(0);
    expect(notasDe(r)).toEqual([0, 0, 0, 0, 0]);
    expect(r.penalidades.some((p) => p.includes("insuficiente"))).toBe(true);
  });

  it("oito linhas não anula", () => {
    const r = normaliza(avaliacao({ linhas: 8 }));
    expect(r.nota_total).toBe(800);
    expect(r.penalidades).toEqual([]);
  });
});

describe("cópia dos textos motivadores", () => {
  it("desconta linhas mas não anula", () => {
    const r = normaliza(avaliacao({ linhas: 28, linhas_copiadas: 3 }));
    expect(r.linhas_validas).toBe(25);
    expect(r.nota_total).toBe(800);
    expect(r.penalidades).toEqual([]);
  });

  it("anula quando derruba abaixo do mínimo", () => {
    const r = normaliza(avaliacao({ linhas: 25, linhas_copiadas: 20 }));
    expect(r.linhas_validas).toBe(5);
    expect(r.nota_total).toBe(0);
  });

  it("recusa mais linhas copiadas do que escritas", () => {
    expect(() => normaliza(avaliacao({ linhas: 10, linhas_copiadas: 11 })))
      .toThrow(/linhas_copiadas/);
  });
});

describe("causas de anulação", () => {
  it.each(Object.keys(ANULA))("%s zera tudo", (enquadramento) => {
    const r = normaliza(avaliacao({ enquadramento }));
    expect(r.nota_total).toBe(0);
    expect(notasDe(r)).toEqual([0, 0, 0, 0, 0]);
    expect(r.anulada).toBe(true);
  });

  it("a lista cobre a cartilha", () => {
    expect(new Set(Object.keys(ANULA))).toEqual(
      new Set([
        "fuga_total", "nao_dissertativo", "parte_desconectada", "improperios",
        "identificacao", "lingua_estrangeira", "ilegivel", "em_branco",
      ])
    );
  });

  it("duas causas simultâneas aparecem juntas", () => {
    const r = normaliza(avaliacao({ linhas: 3, enquadramento: "fuga_total" }));
    expect(r.penalidades).toHaveLength(2);
  });
});

describe("tangenciamento", () => {
  it("não anula", () => {
    expect(normaliza(avaliacao({ enquadramento: "tangenciamento" })).anulada).toBe(false);
  });

  it("limita C2, C3 e C5 em quarenta", () => {
    const r = normaliza(
      avaliacao({ notas: [200, 200, 200, 200, 200], enquadramento: "tangenciamento" })
    );
    expect(notasDe(r)).toEqual([200, 40, 40, 200, 40]);
    expect(r.nota_total).toBe(520);
  });

  it("não sobe nota que já era baixa", () => {
    const r = normaliza(
      avaliacao({ notas: [160, 0, 40, 160, 0], enquadramento: "tangenciamento" })
    );
    expect(notasDe(r)).toEqual([160, 0, 40, 160, 0]);
  });
});

describe("direitos humanos", () => {
  it("zera só a C5", () => {
    const r = normaliza(avaliacao({ fere_direitos_humanos: true }));
    expect(notasDe(r)).toEqual([160, 160, 160, 160, 0]);
    expect(r.nota_total).toBe(640);
  });

  it("convive com tangenciamento", () => {
    const r = normaliza(
      avaliacao({
        notas: [200, 200, 200, 200, 200],
        enquadramento: "tangenciamento",
        fere_direitos_humanos: true,
      })
    );
    expect(notasDe(r)).toEqual([200, 40, 40, 200, 0]);
  });
});

describe("validação: falha fechada", () => {
  it("recusa enquadramento desconhecido", () => {
    expect(() => normaliza(avaliacao({ enquadramento: "fuga" }))).toThrow(AvaliacaoInvalida);
  });

  it.each([[150], [999], ["160" as unknown as number], [40.5]])(
    "recusa nota %p fora do grid",
    (nota) => {
      expect(() => normaliza(avaliacao({ notas: [nota, 160, 160, 160, 160] })))
        .toThrow(/grid/);
    }
  );

  it("recusa linhas negativo", () => {
    expect(() => normaliza(avaliacao({ linhas: -3 }))).toThrow(/linhas/);
  });

  it("recusa linhas como texto", () => {
    expect(() => normaliza(avaliacao({ linhas: "25" as unknown as number })))
      .toThrow(/linhas/);
  });

  it("recusa avaliação sem linhas", () => {
    const crua = avaliacao();
    delete (crua as Partial<AvaliacaoCrua>).linhas;
    expect(() => normaliza(crua)).toThrow(/linhas/);
  });

  it("recusa avaliação sem as cinco competências", () => {
    const crua = avaliacao();
    crua.competencias = crua.competencias.slice(0, 4);
    expect(() => normaliza(crua)).toThrow(/5 competências/);
  });

  it("recusa competência repetida", () => {
    const crua = avaliacao();
    crua.competencias[4].numero = 1;
    expect(() => normaliza(crua)).toThrow(/repetida/);
  });
});

describe("não mutar a entrada", () => {
  it("não muda as notas recebidas", () => {
    const crua = avaliacao({ enquadramento: "fuga_total" });
    normaliza(crua);
    expect(crua.competencias.map((c) => c.nota)).toEqual([160, 160, 160, 160, 160]);
  });

  it("não compartilha as listas de melhorias", () => {
    const crua = avaliacao();
    normaliza(crua).competencias[0].melhorias.push("X");
    expect(crua.competencias[0].melhorias).toEqual(["a", "b"]);
  });
});

describe("schema enviado ao modelo", () => {
  it("não usa recursos que a API rejeita", () => {
    const texto = JSON.stringify(AVALIACAO_SCHEMA);
    for (const proibido of ["minimum", "maximum", "minLength", "maxLength",
                            "multipleOf", "minItems", "maxItems", "pattern"]) {
      expect(texto).not.toContain(proibido);
    }
  });

  it("fecha objetos em todos os níveis", () => {
    expect(AVALIACAO_SCHEMA.additionalProperties).toBe(false);
    expect(AVALIACAO_SCHEMA.properties.competencias.items.additionalProperties).toBe(false);
  });

  it("não pede nota total nem contagem de linhas ao modelo", () => {
    const props = Object.keys(AVALIACAO_SCHEMA.properties);
    expect(props).not.toContain("nota_total");
    expect(props).not.toContain("linhas");
    expect(props).not.toContain("linhas_copiadas");
  });

  it("o enum de notas não é o mesmo objeto da constante", () => {
    expect(AVALIACAO_SCHEMA.properties.competencias.items.properties.nota.enum)
      .not.toBe(NOTAS_VALIDAS);
  });
});
