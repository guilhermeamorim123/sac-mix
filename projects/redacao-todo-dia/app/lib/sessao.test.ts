/**
 * Testes do acesso por link assinado.
 *
 * Um furo aqui deixa qualquer pessoa entrar de graça, ou entrar como outra.
 * Cada teste abaixo é um jeito concreto de tentar isso.
 */

import { describe, expect, it } from "vitest";

import { TokenInvalido, VALIDADE_PADRAO_MS, criaToken, leToken } from "./sessao";

const SEGREDO = "segredo-de-teste-com-tamanho-decente-123456";
const AGORA = 1_755_500_000_000;

describe("ida e volta", () => {
  it("lê de volta o que assinou", () => {
    const token = criaToken({ email: "aluno@email.com", plano: "completo" }, SEGREDO, AGORA);
    const sessao = leToken(token, SEGREDO, AGORA);
    expect(sessao.email).toBe("aluno@email.com");
    expect(sessao.plano).toBe("completo");
    expect(sessao.expiraEm).toBe(AGORA + VALIDADE_PADRAO_MS);
  });

  it("normaliza o e-mail para minúsculas e sem espaço", () => {
    const token = criaToken({ email: "  Aluno@Email.COM ", plano: "corretor" }, SEGREDO, AGORA);
    expect(leToken(token, SEGREDO, AGORA).email).toBe("aluno@email.com");
  });
});

describe("assinatura", () => {
  it("recusa token assinado com outro segredo", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, "outro-segredo", AGORA);
    expect(() => leToken(token, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });

  it("recusa payload adulterado", () => {
    const token = criaToken({ email: "aluno@email.com", plano: "corretor" }, SEGREDO, AGORA);
    const [, assinatura] = token.split(".");
    const forjado = Buffer.from(
      JSON.stringify({ email: "outro@email.com", plano: "completo", expiraEm: AGORA + 1e9 })
    ).toString("base64url");
    expect(() => leToken(`${forjado}.${assinatura}`, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });

  it("recusa upgrade de plano por adulteração", () => {
    // O payload é base64, então trocar a string "corretor" no token não faz
    // nada. Para adulterar de verdade é preciso decodificar, mexer e recodificar
    // mantendo a assinatura antiga — que é exatamente o que um atacante faria.
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    const [corpo, assinatura] = token.split(".");
    const payload = JSON.parse(Buffer.from(corpo, "base64url").toString("utf8"));
    expect(payload.plano).toBe("corretor");
    payload.plano = "completo";
    const forjado = Buffer.from(JSON.stringify(payload)).toString("base64url");
    expect(forjado).not.toBe(corpo);
    expect(() => leToken(`${forjado}.${assinatura}`, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });

  it("recusa assinatura vazia", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    expect(() => leToken(`${token.split(".")[0]}.`, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });

  it("recusa assinatura de tamanho diferente sem quebrar", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    expect(() => leToken(`${token.split(".")[0]}.abc`, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });
});

describe("validade", () => {
  it("recusa token expirado", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    expect(() => leToken(token, SEGREDO, AGORA + VALIDADE_PADRAO_MS + 1)).toThrow(/expirado/);
  });

  it("recusa exatamente no instante da expiração", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    expect(() => leToken(token, SEGREDO, AGORA + VALIDADE_PADRAO_MS)).toThrow(/expirado/);
  });

  it("aceita um instante antes", () => {
    const token = criaToken({ email: "a@b.com", plano: "corretor" }, SEGREDO, AGORA);
    expect(leToken(token, SEGREDO, AGORA + VALIDADE_PADRAO_MS - 1).email).toBe("a@b.com");
  });
});

describe("entradas malformadas", () => {
  it.each(["", "sem-ponto", ".", "a.b.c.d", "null"])("recusa %p", (entrada) => {
    expect(() => leToken(entrada, SEGREDO, AGORA)).toThrow();
  });

  it("recusa payload que não é JSON", () => {
    const corpo = Buffer.from("nao é json").toString("base64url");
    const { createHmac } = require("node:crypto");
    const assinatura = createHmac("sha256", SEGREDO).update(corpo).digest("base64url");
    expect(() => leToken(`${corpo}.${assinatura}`, SEGREDO, AGORA)).toThrow(TokenInvalido);
  });

  it("recusa plano desconhecido mesmo com assinatura válida", () => {
    const corpo = Buffer.from(
      JSON.stringify({ email: "a@b.com", plano: "vitalicio", expiraEm: AGORA + 1e9 })
    ).toString("base64url");
    const { createHmac } = require("node:crypto");
    const assinatura = createHmac("sha256", SEGREDO).update(corpo).digest("base64url");
    expect(() => leToken(`${corpo}.${assinatura}`, SEGREDO, AGORA)).toThrow(/plano desconhecido/);
  });
});

describe("segredo ausente", () => {
  it("não assina sem segredo", () => {
    expect(() => criaToken({ email: "a@b.com", plano: "corretor" }, "")).toThrow(/segredo/);
  });

  it("não confere sem segredo", () => {
    expect(() => leToken("qualquer.coisa", "")).toThrow(/segredo/);
  });
});
