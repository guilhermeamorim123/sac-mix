/**
 * Acesso por link assinado.
 *
 * Quem compra recebe uma URL com um token que carrega o e-mail e a validade,
 * assinado com HMAC-SHA256 usando um segredo que só existe no servidor. O app
 * confere a assinatura e grava um cookie de sessão.
 *
 * Isso não é gerência de senha — é uma URL-capacidade: quem tem o link tem o
 * acesso, como um link de convite. O que protege é a assinatura: sem o segredo
 * não dá para forjar um token para outro e-mail.
 *
 * Duas regras que este arquivo existe para garantir:
 *   1. comparação de assinatura em tempo constante, para não vazar o segredo
 *      byte a byte por medição de tempo;
 *   2. validade sempre conferida — token sem expiração é chave eterna.
 */

import { createHmac, timingSafeEqual } from "node:crypto";

/** Um token vale 30 dias. Cabe o produto inteiro e limita o estrago se vazar. */
export const VALIDADE_PADRAO_MS = 30 * 24 * 60 * 60 * 1000;

export type Plano = "corretor" | "completo";

export interface Sessao {
  email: string;
  plano: Plano;
  /** epoch em milissegundos */
  expiraEm: number;
}

export class TokenInvalido extends Error {}

function base64url(dados: Buffer | string): string {
  return Buffer.from(dados)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function deBase64url(texto: string): Buffer {
  return Buffer.from(texto.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

function assina(corpo: string, segredo: string): string {
  return base64url(createHmac("sha256", segredo).update(corpo).digest());
}

/** Gera o token que vai na URL de acesso enviada ao comprador. */
export function criaToken(
  sessao: Omit<Sessao, "expiraEm"> & { expiraEm?: number },
  segredo: string,
  agora: number = Date.now()
): string {
  if (!segredo) throw new Error("segredo de sessão ausente");
  const payload: Sessao = {
    email: sessao.email.trim().toLowerCase(),
    plano: sessao.plano,
    expiraEm: sessao.expiraEm ?? agora + VALIDADE_PADRAO_MS,
  };
  const corpo = base64url(JSON.stringify(payload));
  return `${corpo}.${assina(corpo, segredo)}`;
}

/** Confere assinatura e validade. Lança TokenInvalido em qualquer problema. */
export function leToken(token: string, segredo: string, agora: number = Date.now()): Sessao {
  if (!segredo) throw new Error("segredo de sessão ausente");
  if (typeof token !== "string" || !token.includes(".")) {
    throw new TokenInvalido("token malformado");
  }

  const [corpo, assinatura] = token.split(".", 2);
  const esperada = assina(corpo, segredo);

  const a = deBase64url(assinatura);
  const b = deBase64url(esperada);
  // timingSafeEqual exige o mesmo tamanho; comparar tamanho antes não vaza nada
  // útil, porque o tamanho da assinatura é fixo e público.
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    throw new TokenInvalido("assinatura não confere");
  }

  let payload: Sessao;
  try {
    payload = JSON.parse(deBase64url(corpo).toString("utf8"));
  } catch {
    throw new TokenInvalido("payload ilegível");
  }

  if (!payload?.email || !payload?.plano || typeof payload.expiraEm !== "number") {
    throw new TokenInvalido("payload incompleto");
  }
  if (payload.plano !== "corretor" && payload.plano !== "completo") {
    throw new TokenInvalido(`plano desconhecido: ${payload.plano}`);
  }
  if (agora >= payload.expiraEm) {
    throw new TokenInvalido("token expirado");
  }

  return payload;
}
