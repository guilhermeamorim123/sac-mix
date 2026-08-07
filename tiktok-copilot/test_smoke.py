"""Testes rapidos da logica pura (sem rede, sem API key).

    python test_smoke.py
"""
from catalog import Catalog
from config import INTENTS_AUTO_PADRAO, Settings
from models import AUTO_SAFE_INTENTS, Analysis, extract_whatsapp
from store import avaliar

falhas = 0


def check(nome, obtido, esperado):
    global falhas
    ok = obtido == esperado
    if not ok:
        falhas += 1
    print(f"  {'ok    ' if ok else 'FALHOU'} {nome:44} -> {obtido!r}")


print("--- Captura de WhatsApp ---")
check("zap com hifen",        extract_whatsapp("meu zap 11 98765-4321"), "5511987654321")
check("ddd entre parenteses", extract_whatsapp("chama no (21)999887766"), "5521999887766")
check("com ddi e espacos",    extract_whatsapp("+55 31 9 8888 7777"), "5531988887777")
check("colado no texto",      extract_whatsapp("me chama 11987654321 pf"), "5511987654321")
check("preco nao e telefone", extract_whatsapp("quanto custa? 1199"), None)
check("cep nao e telefone",   extract_whatsapp("CEP 01310-100"), None)
check("fixo e ignorado",      extract_whatsapp("tel fixo 1133334444"), None)

print("\n--- Trava de auto-envio ---")
check("preco + sem humano = envia",
      Analysis("1", "preco", 5, "R$89,90", requires_human=False).can_auto_send(), True)
check("reclamacao nunca envia",
      Analysis("2", "reclamacao", 8, "opa", requires_human=False).can_auto_send(), False)
check("requires_human trava",
      Analysis("3", "preco", 5, "x", requires_human=True).can_auto_send(), False)
check("intents seguros", sorted(AUTO_SAFE_INTENTS),
      ["como_comprar", "frete", "prazo", "preco"])

print("\n--- Configuracoes vindas do painel ---")
restrito = Settings.from_row({"auto_reply_enabled": True, "max_por_minuto": 2,
                              "intents_auto": ["preco"], "hot_lead_threshold": 8})
check("loja restringe a lista", sorted(restrito.intents_auto), ["preco"])
check("frete deixa de auto-enviar",
      Analysis("4", "frete", 5, "R$14,90", requires_human=False)
      .can_auto_send(restrito.intents_auto), False)
check("preco continua auto-enviando",
      Analysis("5", "preco", 5, "R$89,90", requires_human=False)
      .can_auto_send(restrito.intents_auto), True)

# O painel nao deve conseguir liberar reclamacao nem no banco.
perigoso = Settings.from_row({"intents_auto": ["preco", "reclamacao", "outro"]})
check("intent perigoso e descartado", sorted(perigoso.intents_auto), ["preco"])
check("padrao quando a coluna vem vazia",
      sorted(Settings.from_row({}).intents_auto), sorted(INTENTS_AUTO_PADRAO))

print("\n--- Triagem: NUNCA filtrar quem demonstra interesse ---")
from models import ChatMessage
from triagem import Triagem, analise_local

_cat = Catalog.from_rows(
    produtos=[{"nome": "Fone Bluetooth TWS Pro", "preco": 89.9, "estoque": 10,
               "cores": [], "tamanhos": [], "obs": None}],
    frete=[], conhecimento=[],
)
t = Triagem(_cat)
msg = lambda txt: ChatMessage(message_id="x", user_id="u", username="u",
                              nickname="U", text=txt)

# Se algum destes virar True, o filtro esta jogando venda fora.
INTERESSE = [
    "quanto custa?", "qual o preco", "tem em preto", "ainda tem?",
    "quero 2", "vou levar", "manda o link", "como faco pra comprar",
    "chega em quanto tempo", "faz frete pro ceara", "aceita pix?",
    "parcela em 3x", "meu zap 11 98765-4321", "11987654321",
    "esse fone e bom?", "o fone tem garantia", "qual o tamanho",
    "nao chegou meu pedido", "demorou demais isso ai",
    "boa noite, tem esse produto ainda", "oi quanto e",
    "manda no whats", "top esse fone, quanto?",
]
falhas_criticas = 0
for txt in INTERESSE:
    if t.trivial(msg(txt)):
        falhas_criticas += 1
        print(f"  FALHOU  FILTROU INTERESSE: {txt!r}")
check("nenhuma mensagem de interesse foi filtrada", falhas_criticas, 0)

print("\n--- Triagem: ruido que nao deve custar token ---")
RUIDO = ["oi", "boa noite", "top", "kkkkkk", "❤️❤️❤️", "👏", "...", "amei",
         "lindo demais", "top demais", "obrigado", "vlw", "primeira vez aqui",
         "bom dia", "parabens", "show", "aaaaaa", "ok", "sim", "tchau"]
passou = [txt for txt in RUIDO if not t.trivial(msg(txt))]
check("ruido filtrado", len(passou), 0)
if passou:
    print(f"         passaram para a IA: {passou}")
check("taxa de filtragem contabilizada",
      round(Triagem(_cat).taxa_filtrada), 0)

# Citar o produto e sinal de interesse mesmo sem pergunta.
check("nome do produto nao e trivial", t.trivial(msg("esse fone")), False)
check("frase longa nao e trivial",
      t.trivial(msg("boa noite pessoal tudo bem com voces hoje")), False)

print("\n--- Triagem: analise local ---")
a = analise_local(msg("top demais"))
check("elogio classificado", a.intent, "elogio")
check("score zero", a.lead_score, 0)
check("sem sugestao (fica fora da fila)", a.suggested_reply, "")
check("nao pede humano", a.requires_human, False)
check("nao auto-envia", a.can_auto_send(), False)
check("emoji vira outro", analise_local(msg("❤️")).intent, "outro")

# Taxa medida num lote realista de live.
t2 = Triagem(_cat)
lote = [msg(x) for x in RUIDO + INTERESSE[:8]]
para_ia, triviais = t2.separar(lote)
print(f"\n  lote de {len(lote)}: {len(triviais)} filtradas, {len(para_ia)} para a IA "
      f"({t2.taxa_filtrada:.0f}% sem token)")

print("\n--- Avaliacao de live ---")
for resumo, esperado in [
    ({"titulo": "forte",  "duracao_min": 75, "comentarios": 900, "leads_captados": 90}, "boa"),
    ({"titulo": "media",  "duracao_min": 80, "comentarios": 200, "leads_captados": 10}, "regular"),
    ({"titulo": "fraca",  "duracao_min": 70, "comentarios": 40,  "leads_captados": 1},  "ruim"),
]:
    score, rating, rec = avaliar(resumo)
    check(f"{resumo['titulo']} ({score}/100)", rating, esperado)
    print(f"         {rec}")

print("\n--- Catalogo do arquivo local ---")
local = Catalog.from_json()
bloco = local.as_prompt_block()
check("catalogo nao vazio", len(bloco) > 100, True)
check("marca esgotado", "esgotado" in bloco, True)

print("\n--- Catalogo vindo do banco ---")
# Mesma forma das linhas de `produtos`, `frete_regras` e `base_conhecimento`.
banco = Catalog.from_rows(
    produtos=[
        {"nome": "Fone TWS", "preco": "89.90", "estoque": 40,
         "cores": ["preto"], "tamanhos": [], "obs": "12h de bateria"},
        {"nome": "Smartwatch D20", "preco": 59.9, "estoque": 0,
         "cores": None, "tamanhos": None, "obs": None},
    ],
    frete=[{"regiao": "Sudeste", "descricao": "R$ 14,90 - 3 a 5 dias uteis"}],
    conhecimento=[{"titulo": "Troca", "conteudo": "7 dias corridos apos o recebimento."}],
)
bloco_banco = banco.as_prompt_block()
check("preco em string vira numero", banco.produtos[0]["preco"], 89.9)
check("preco formatado em BRL", "R$89,90" in bloco_banco, True)
check("estoque zero vira esgotado", "esgotado" in bloco_banco, True)
check("cores nulas viram lista vazia", banco.produtos[1]["cores"], [])
check("frete entra no prompt", "FRETE E PRAZO" in bloco_banco, True)
check("base de conhecimento entra", "BASE DE CONHECIMENTO" in bloco_banco, True)
check("fingerprint muda com o catalogo",
      banco.fingerprint == local.fingerprint, False)
check("fingerprint estavel para o mesmo dado",
      banco.fingerprint == Catalog.from_rows(
          produtos=[
              {"nome": "Fone TWS", "preco": 89.9, "estoque": 40,
               "cores": ["preto"], "tamanhos": [], "obs": "12h de bateria"},
              {"nome": "Smartwatch D20", "preco": 59.9, "estoque": 0,
               "cores": [], "tamanhos": [], "obs": None},
          ],
          frete=[{"regiao": "Sudeste", "descricao": "R$ 14,90 - 3 a 5 dias uteis"}],
          conhecimento=[{"titulo": "Troca", "conteudo": "7 dias corridos apos o recebimento."}],
      ).fingerprint, True)
check("catalogo sem produtos e vazio", Catalog().vazio, True)

print("\n" + bloco_banco)

print(f"\n{'TUDO PASSOU' if falhas == 0 else f'{falhas} FALHA(S)'}")
raise SystemExit(1 if falhas else 0)
