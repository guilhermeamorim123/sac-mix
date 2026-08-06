"""Testes rapidos da logica pura (sem rede, sem API key).

    python test_smoke.py
"""
import catalog
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
      Analysis("1", "preco", 5, "R$89,90", requires_human=False).can_auto_send, True)
check("reclamacao nunca envia",
      Analysis("2", "reclamacao", 8, "opa", requires_human=False).can_auto_send, False)
check("requires_human trava",
      Analysis("3", "preco", 5, "x", requires_human=True).can_auto_send, False)
check("intents seguros", sorted(AUTO_SAFE_INTENTS),
      ["como_comprar", "frete", "prazo", "preco"])

print("\n--- Avaliacao de live ---")
for resumo, esperado in [
    ({"titulo": "forte",  "duracao_min": 75, "comentarios": 900, "leads_captados": 90}, "boa"),
    ({"titulo": "media",  "duracao_min": 80, "comentarios": 200, "leads_captados": 10}, "regular"),
    ({"titulo": "fraca",  "duracao_min": 70, "comentarios": 40,  "leads_captados": 1},  "ruim"),
]:
    score, rating, rec = avaliar(resumo)
    check(f"{resumo['titulo']} ({score}/100)", rating, esperado)
    print(f"         {rec}")

print("\n--- Catalogo no prompt ---")
bloco = catalog.as_prompt_block(catalog.load(), catalog.load_frete())
check("catalogo nao vazio", len(bloco) > 100, True)
check("marca esgotado", "esgotado" in bloco, True)
print("\n" + bloco[:320] + "\n...")

print(f"\n{'TUDO PASSOU' if falhas == 0 else f'{falhas} FALHA(S)'}")
raise SystemExit(1 if falhas else 0)
