/**
 * As duas chamadas ao Claude: transcrever a foto e avaliar o texto.
 *
 * Porte de `corretor/api.py`. As etapas são separadas de propósito: o maior
 * risco técnico é o modelo ler a letra errado e corrigir o texto errado.
 * Separando, o erro de leitura vira uma tela de conferência de dez segundos.
 */

import Anthropic from "@anthropic-ai/sdk";

import { AVALIACAO_SCHEMA, normaliza, type Avaliacao, type AvaliacaoCrua } from "./regras";
import { RUBRICA, TRANSCRICAO } from "./prompts";

export const MODELO = "claude-opus-5";
export const MAX_TOKENS = 16000;

/**
 * O thinking do Opus 5 vem ligado e conta para max_tokens e para o custo.
 * Transcrição é OCR, não raciocínio — roda barato. Avaliação é julgamento.
 * Estes dois são a alavanca de custo mais direta: meça antes de baixar.
 */
export const EFFORT_TRANSCRICAO = "low";
export const EFFORT_AVALIACAO = "high";

/** Preço do claude-opus-5 em USD por 1M de tokens. */
const PRECO_ENTRADA = 5.0;
const PRECO_SAIDA = 25.0;
const FATOR_ESCRITA_CACHE = 1.25;
const FATOR_LEITURA_CACHE = 0.1;

const FORMATOS_ACEITOS = ["image/jpeg", "image/png", "image/webp", "image/gif"] as const;
export type FormatoAceito = (typeof FORMATOS_ACEITOS)[number];

export class RecusaDaAPI extends Error {}
export class FotoIlegivel extends Error {}
export class RespostaSemTexto extends Error {}
export class TranscricaoSemContagem extends Error {}
export class FormatoNaoSuportado extends Error {}

export interface Uso {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number | null;
  cache_read_input_tokens?: number | null;
}

export interface Transcricao {
  texto: string;
  linhas: number;
}

export function ehFormatoAceito(tipo: string): tipo is FormatoAceito {
  return (FORMATOS_ACEITOS as readonly string[]).includes(tipo);
}

function textoDaResposta(resposta: Anthropic.Message): string {
  if (resposta.stop_reason === "refusal") {
    throw new RecusaDaAPI("a API recusou a requisição");
  }
  for (const bloco of resposta.content) {
    if (bloco.type === "text") return bloco.text;
  }
  throw new RespostaSemTexto(
    `resposta sem bloco de texto (stop_reason=${resposta.stop_reason}). ` +
      "No Opus 5 o thinking conta para max_tokens — tente aumentar MAX_TOKENS."
  );
}

/** Custo da chamada em dólares, a partir do `usage` da resposta. */
export function custoUsd(uso: Uso): number {
  const escritaCache = uso.cache_creation_input_tokens ?? 0;
  const leituraCache = uso.cache_read_input_tokens ?? 0;
  const entrada =
    uso.input_tokens + escritaCache * FATOR_ESCRITA_CACHE + leituraCache * FATOR_LEITURA_CACHE;
  return (entrada * PRECO_ENTRADA) / 1e6 + (uso.output_tokens * PRECO_SAIDA) / 1e6;
}

/** Lê a foto e devolve o texto transcrito. Não avalia nada. */
export async function transcrever(
  cliente: Anthropic,
  imagemBase64: string,
  mediaType: string
): Promise<{ transcricao: Transcricao; uso: Uso }> {
  if (!ehFormatoAceito(mediaType)) {
    throw new FormatoNaoSuportado(
      `formato não suportado: ${mediaType}. Aceitos: ${FORMATOS_ACEITOS.join(", ")}`
    );
  }

  const resposta = await cliente.messages.create({
    model: MODELO,
    max_tokens: MAX_TOKENS,
    output_config: { effort: EFFORT_TRANSCRICAO },
    messages: [
      {
        role: "user",
        content: [
          { type: "image", source: { type: "base64", media_type: mediaType, data: imagemBase64 } },
          { type: "text", text: TRANSCRICAO },
        ],
      },
    ],
  } as Anthropic.MessageCreateParamsNonStreaming);

  const bruto = textoDaResposta(resposta).trim();
  if (bruto.startsWith("FOTO_ILEGIVEL")) {
    throw new FotoIlegivel("o modelo não conseguiu ler a foto");
  }

  const cabecalho = /^LINHAS:\s*(\d+)\s*\n+/.exec(bruto);
  if (!cabecalho) {
    throw new TranscricaoSemContagem(
      "a transcrição veio sem o cabeçalho 'LINHAS: <n>'. Esse número dispara a " +
        "regra de anulação por texto insuficiente — sem ele, avaliar produziria " +
        "nota errada."
    );
  }

  return {
    transcricao: {
      texto: bruto.slice(cabecalho[0].length).trim(),
      linhas: parseInt(cabecalho[1], 10),
    },
    uso: resposta.usage as Uso,
  };
}

/**
 * Avalia o texto transcrito.
 *
 * `linhas` vem da transcrição, não do modelo avaliador — ele não vê a foto, e
 * esse número dispara a regra de anulação por texto insuficiente.
 */
export async function avaliar(
  cliente: Anthropic,
  texto: string,
  tema: string,
  linhas: number,
  linhasCopiadas = 0
): Promise<{ avaliacao: Avaliacao; uso: Uso }> {
  const resposta = await cliente.messages.create({
    model: MODELO,
    max_tokens: MAX_TOKENS,
    output_config: {
      effort: EFFORT_AVALIACAO,
      format: { type: "json_schema", schema: AVALIACAO_SCHEMA },
    },
    system: [{ type: "text", text: RUBRICA, cache_control: { type: "ephemeral" } }],
    messages: [
      {
        role: "user",
        content:
          `TEMA PROPOSTO:\n${tema}\n\n` +
          `REDAÇÃO DO ALUNO (transcrita da foto):\n${texto}`,
      },
    ],
  } as Anthropic.MessageCreateParamsNonStreaming);

  const crua = JSON.parse(textoDaResposta(resposta)) as AvaliacaoCrua;
  crua.linhas = linhas;
  crua.linhas_copiadas = linhasCopiadas;

  return { avaliacao: normaliza(crua), uso: resposta.usage as Uso };
}
