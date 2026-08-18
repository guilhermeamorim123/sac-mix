/**
 * Contrato da avaliação e as regras de nota do ENEM.
 *
 * O modelo julga cada competência. Toda regra determinística fica aqui —
 * somar, aplicar tetos e anular — porque é onde LLM erra sem ganhar nada em
 * troca.
 *
 * Porte fiel de `corretor/schema.py`, que tem 38 testes em Python. Os testes
 * daqui são os mesmos, para o porte não introduzir divergência.
 *
 * Regras conferidas contra a Cartilha do Participante do INEP:
 * https://download.inep.gov.br/publicacoes/institucionais/avaliacoes_e_exames_da_educacao_basica/a_redacao_no_enem_2025_cartilha_do_participante.pdf
 */

export const COMPETENCIAS: Record<number, string> = {
  1: "Domínio da modalidade escrita formal da língua portuguesa",
  2: "Compreender a proposta e aplicar conceitos de várias áreas do conhecimento",
  3: "Selecionar, relacionar, organizar e interpretar informações em defesa de um ponto de vista",
  4: "Conhecimento dos mecanismos linguísticos de construção da argumentação",
  5: "Elaborar proposta de intervenção que respeite os direitos humanos",
};

/** O ENEM só dá nota em múltiplos de 40, de 0 a 200, por competência. */
export const NOTAS_VALIDAS: readonly number[] = [0, 40, 80, 120, 160, 200];

/**
 * Causas de nota zero na redação inteira, conforme a cartilha.
 * Tangenciamento NÃO está aqui — tem tratamento próprio, ver TETO_TANGENCIAMENTO.
 * Cópia dos textos motivadores também NÃO está aqui — desconta linhas, não anula.
 */
export const ANULA: Record<string, string> = {
  fuga_total: "fuga total ao tema",
  nao_dissertativo: "não obediência ao tipo dissertativo-argumentativo",
  parte_desconectada: "parte deliberadamente desconectada do tema",
  improperios: "impropérios, desenhos ou outra forma proposital de anulação",
  identificacao: "identificação fora do espaço destinado",
  lingua_estrangeira: "texto predominantemente em língua estrangeira",
  ilegivel: "texto ilegível",
  em_branco: "folha em branco",
};

export const ENQUADRAMENTOS: readonly string[] = [
  "ok",
  "tangenciamento",
  ...Object.keys(ANULA),
];

/** Tangenciar o tema trava C2, C3 e C5 em no máximo 40 pontos cada. */
export const TETO_TANGENCIAMENTO = 40;
export const COMPETENCIAS_TANGENCIADAS: readonly number[] = [2, 3, 5];

/** "Extensão de até 7 linhas manuscritas" anula; a partir de 8 vale. */
export const LINHAS_MINIMAS = 8;

export const AVALIACAO_SCHEMA = {
  type: "object",
  properties: {
    competencias: {
      type: "array",
      items: {
        type: "object",
        properties: {
          numero: { type: "integer", enum: [1, 2, 3, 4, 5] },
          nota: { type: "integer", enum: [...NOTAS_VALIDAS] },
          justificativa: { type: "string" },
          melhorias: { type: "array", items: { type: "string" } },
        },
        required: ["numero", "nota", "justificativa", "melhorias"],
        additionalProperties: false,
      },
    },
    enquadramento: { type: "string", enum: [...ENQUADRAMENTOS] },
    fere_direitos_humanos: { type: "boolean" },
    resumo: { type: "string" },
  },
  required: ["competencias", "enquadramento", "fere_direitos_humanos", "resumo"],
  additionalProperties: false,
} as const;

export interface Competencia {
  numero: number;
  nota: number;
  justificativa: string;
  melhorias: string[];
}

/** O que o modelo avaliador devolve. Note que não tem `linhas`: ele não vê a foto. */
export interface AvaliacaoCrua {
  competencias: Competencia[];
  enquadramento: string;
  fere_direitos_humanos: boolean;
  resumo: string;
  /** Injetado pelo código a partir da transcrição, nunca pelo modelo. */
  linhas?: number;
  linhas_copiadas?: number;
}

export interface Avaliacao {
  competencias: Competencia[];
  enquadramento: string;
  fere_direitos_humanos: boolean;
  resumo: string;
  linhas: number;
  linhas_copiadas: number;
  linhas_validas: number;
  nota_total: number;
  penalidades: string[];
  anulada: boolean;
}

/** Erro de contrato: a resposta do modelo não faz sentido. Falhar alto é melhor
 *  que produzir nota errada com aparência de certa. */
export class AvaliacaoInvalida extends Error {}

function validaCompetencias(avaliacao: AvaliacaoCrua): Map<number, Competencia> {
  const porNumero = new Map<number, Competencia>();
  for (const item of avaliacao.competencias ?? []) {
    if (porNumero.has(item.numero)) {
      throw new AvaliacaoInvalida(`competência ${item.numero} veio repetida`);
    }
    if (!Number.isInteger(item.nota) || !NOTAS_VALIDAS.includes(item.nota)) {
      throw new AvaliacaoInvalida(
        `competência ${item.numero}: nota ${JSON.stringify(item.nota)} fora do ` +
          `grid ${NOTAS_VALIDAS.join(", ")}`
      );
    }
    porNumero.set(item.numero, { ...item, melhorias: [...(item.melhorias ?? [])] });
  }
  const numeros = [...porNumero.keys()].sort((a, b) => a - b);
  if (numeros.join(",") !== "1,2,3,4,5") {
    throw new AvaliacaoInvalida(
      `esperava as 5 competências, vieram ${JSON.stringify(numeros)}`
    );
  }
  return porNumero;
}

function validaContagem(valor: unknown, chave: string): number {
  const n = valor ?? 0;
  if (!Number.isInteger(n) || (n as number) < 0) {
    throw new AvaliacaoInvalida(
      `${chave} deve ser inteiro não-negativo, veio ${JSON.stringify(valor)}`
    );
  }
  return n as number;
}

/**
 * Aplica as regras do ENEM e calcula a nota total.
 *
 * `linhas` é obrigatório e vem da transcrição, não do modelo avaliador — ele
 * não vê a foto, e esse número dispara a anulação por texto insuficiente.
 */
export function normaliza(avaliacao: AvaliacaoCrua): Avaliacao {
  const competencias = validaCompetencias(avaliacao);

  const enquadramento = avaliacao.enquadramento;
  if (!ENQUADRAMENTOS.includes(enquadramento)) {
    throw new AvaliacaoInvalida(
      `enquadramento desconhecido: ${JSON.stringify(enquadramento)}. ` +
        `Esperado um de ${ENQUADRAMENTOS.join(", ")}`
    );
  }

  if (avaliacao.linhas === undefined || avaliacao.linhas === null) {
    throw new AvaliacaoInvalida(
      "avaliação sem 'linhas' — o número vem da transcrição, não do modelo " +
        "avaliador; quem chama precisa injetá-lo"
    );
  }
  const linhas = validaContagem(avaliacao.linhas, "linhas");
  const copiadas = validaContagem(avaliacao.linhas_copiadas, "linhas_copiadas");
  if (copiadas > linhas) {
    throw new AvaliacaoInvalida(
      `linhas_copiadas (${copiadas}) é maior que linhas (${linhas})`
    );
  }
  const linhasValidas = linhas - copiadas;

  const penalidades: string[] = [];
  if (enquadramento in ANULA) penalidades.push(ANULA[enquadramento]);
  if (linhasValidas < LINHAS_MINIMAS) {
    penalidades.push(
      `texto insuficiente: ${linhasValidas} linha(s) válida(s), o mínimo é ${LINHAS_MINIMAS}`
    );
  }

  if (penalidades.length > 0) {
    for (const c of competencias.values()) c.nota = 0;
  } else {
    if (enquadramento === "tangenciamento") {
      for (const numero of COMPETENCIAS_TANGENCIADAS) {
        const c = competencias.get(numero)!;
        c.nota = Math.min(c.nota, TETO_TANGENCIAMENTO);
      }
    }
    if (avaliacao.fere_direitos_humanos) competencias.get(5)!.nota = 0;
  }

  const ordenadas = [1, 2, 3, 4, 5].map((n) => competencias.get(n)!);
  return {
    competencias: ordenadas,
    enquadramento,
    fere_direitos_humanos: Boolean(avaliacao.fere_direitos_humanos),
    resumo: avaliacao.resumo,
    linhas,
    linhas_copiadas: copiadas,
    linhas_validas: linhasValidas,
    nota_total: ordenadas.reduce((soma, c) => soma + c.nota, 0),
    penalidades,
    anulada: penalidades.length > 0,
  };
}
