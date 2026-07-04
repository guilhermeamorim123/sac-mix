"""
Standalone ML question auto-responder.
Fetches unanswered buyer questions from Mercado Livre, generates persuasive responses
via Claude (with web search fallback), and posts them automatically.

Designed to run as a GitHub Actions cron job (no Claude Code required).

Environment variables per account (N = 1, 2, 3…):
  ANTHROPIC_API_KEY          Anthropic API key
  ML_CLIENT_ID_N             ML app client ID
  ML_CLIENT_SECRET_N         ML app secret key
  ML_REFRESH_TOKEN_N         ML refresh token (primary credential for GitHub Actions)
  ML_ACCESS_TOKEN_N          ML access token (optional — refreshed automatically on 401)

Optional — SAC Mix IA integration (history + per-product knowledge base in the
Mixfoco app at mixfoco.com.br). When unset, the responder works exactly as before,
just without reporting history or consulting the product knowledge base:
  MIXFOCO_API_URL            Base URL of the Mixfoco API (e.g. https://mixfoco.com.br)
  MIXFOCO_ML_IA_SECRET       Shared secret for /mixfoco/ml-ia/ingest and /kb-produto
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from typing import Optional

import anthropic
import requests

ML_BASE = "https://api.mercadolibre.com"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
MAX_ANSWER_LENGTH = 2000
GENERIC_RESPONSE = (
    "Olá! Para mais detalhes sobre essa especificação, recomendo entrar em contato "
    "pelo chat do Mercado Livre — assim consigo te ajudar com mais precisão. 😊"
)
ESCALATION_KEYWORDS = [
    "preço", "preco", "desconto", "negoc", "valor",
    "devolução", "devolucao", "troca", "reembolso", "cancelar",
    "defeito", "quebrado", "chegou errado", "problema",
    "garantia", "assistência técnica", "assistencia tecnica",
    "ameaça", "ameaca", "processo", "procon", "reclame",
]

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(SCRIPTS_DIR)
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"

MIXFOCO_API_URL = os.environ.get("MIXFOCO_API_URL", "").rstrip("/")
MIXFOCO_ML_IA_SECRET = os.environ.get("MIXFOCO_ML_IA_SECRET", "")


# ── Auth ─────────────────────────────────────────────────────────────────────

def _do_refresh(n: int) -> Optional[str]:
    client_id = os.environ.get(f"ML_CLIENT_ID_{n}", "")
    secret = os.environ.get(f"ML_CLIENT_SECRET_{n}", "")
    refresh = os.environ.get(f"ML_REFRESH_TOKEN_{n}", "")
    if not all([client_id, secret, refresh]):
        return None
    try:
        resp = requests.post(
            ML_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": secret,
                "refresh_token": refresh,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"  [WARN] Falha ao renovar token conta {n}: {e}", file=sys.stderr)
        return None
    data = resp.json()
    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", refresh)
    print(f"  [INFO] Token renovado para conta {n}.")
    # Write refreshed tokens to GITHUB_ENV so the "update secrets" step can persist them
    github_env = os.environ.get("GITHUB_ENV")
    if github_env and new_access:
        with open(github_env, "a") as f:
            f.write(f"NEW_ML_ACCESS_TOKEN_{n}={new_access}\n")
            if new_refresh and new_refresh != refresh:
                f.write(f"NEW_ML_REFRESH_TOKEN_{n}={new_refresh}\n")
    return new_access or None


def get_initial_token(n: int) -> Optional[str]:
    """Return access token for account n, refreshing immediately if only refresh creds are available."""
    access = os.environ.get(f"ML_ACCESS_TOKEN_{n}", "")
    has_refresh = all([
        os.environ.get(f"ML_CLIENT_ID_{n}"),
        os.environ.get(f"ML_CLIENT_SECRET_{n}"),
        os.environ.get(f"ML_REFRESH_TOKEN_{n}"),
    ])
    if not access and has_refresh:
        return _do_refresh(n)
    return access or None


def account_exists(n: int) -> bool:
    return bool(
        os.environ.get(f"ML_ACCESS_TOKEN_{n}")
        or os.environ.get(f"ML_REFRESH_TOKEN_{n}")
    )


# ── ML API ────────────────────────────────────────────────────────────────────

def get_seller_id(token: str) -> Optional[str]:
    resp = requests.get(
        f"{ML_BASE}/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code == 401:
        return None
    resp.raise_for_status()
    return str(resp.json()["id"])


def fetch_questions(token: str) -> Optional[list]:
    """Returns None on 401 (expired token), [] if no questions, list otherwise."""
    seller_id = get_seller_id(token)
    if seller_id is None:
        return None
    questions: list = []
    offset = 0
    while True:
        resp = requests.get(
            f"{ML_BASE}/questions/search",
            params={"seller_id": seller_id, "status": "UNANSWERED", "offset": offset, "limit": 50},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 401:
            return None
        resp.raise_for_status()
        data = resp.json()
        questions.extend(data.get("questions", []))
        if offset + 50 >= data.get("total", 0):
            break
        offset += 50
    return questions


def fetch_item(item_id: str, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{ML_BASE}/items/{item_id}", headers=headers, timeout=15)
    if not resp.ok:
        return {}
    item = resp.json()
    desc_resp = requests.get(f"{ML_BASE}/items/{item_id}/description", headers=headers, timeout=15)
    description = desc_resp.json().get("plain_text", "") if desc_resp.ok else ""
    sale_price = None
    if item.get("sale_price"):
        sale_price = item["sale_price"].get("amount")
    return {
        "id": item["id"],
        "title": item.get("title", ""),
        "price": item.get("price"),
        "sale_price": sale_price,
        "available_quantity": item.get("available_quantity", 0),
        "condition": item.get("condition", ""),
        "attributes": [
            {"id": a.get("id"), "name": a.get("name"), "value_name": a.get("value_name")}
            for a in item.get("attributes", [])
            if a.get("value_name")
        ],
        "description": description,
    }


def post_answer_api(question_id: int, text: str, token: str) -> bool:
    if len(text) > MAX_ANSWER_LENGTH:
        text = text[:MAX_ANSWER_LENGTH]
    resp = requests.post(
        f"{ML_BASE}/answers",
        json={"question_id": question_id, "text": text},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        print(
            f"  [WARN] Erro ao postar Q#{question_id}: {resp.status_code} — {resp.text[:200]}",
            file=sys.stderr,
        )
        return False
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_guidelines() -> str:
    path = os.path.join(AGENT_DIR, "context", "answer-guidelines.md")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def item_to_text(item: dict) -> str:
    lines = [
        f"Título: {item.get('title', '')}",
        f"Condição: {item.get('condition', '')}",
        f"Estoque disponível: {item.get('available_quantity', 0)}",
    ]
    if item.get("price"):
        lines.append(f"Preço: R$ {item['price']}")
    if item.get("sale_price"):
        lines.append(f"Preço promocional: R$ {item['sale_price']}")
    attrs = [
        f"  {a['name']}: {a['value_name']}"
        for a in item.get("attributes", [])[:25]
        if a.get("name") and a.get("value_name")
    ]
    if attrs:
        lines.append("Atributos:\n" + "\n".join(attrs))
    desc = item.get("description", "")
    if desc:
        lines.append(f"Descrição: {desc[:700]}")
    return "\n".join(lines)


def is_escalation(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in ESCALATION_KEYWORDS)


# ── SAC Mix IA integration (history + per-product knowledge base) ────────────
# Best-effort only: network/config issues here must never break the core
# answer-and-post flow, so every call is wrapped and failures are swallowed
# after logging a warning.

def fetch_product_kb(item_id: str) -> str:
    """Fetch active knowledge-base entries for this product from the Mixfoco app.
    Returns an empty string if the integration isn't configured or the call fails."""
    if not (MIXFOCO_API_URL and MIXFOCO_ML_IA_SECRET and item_id):
        return ""
    try:
        resp = requests.get(
            f"{MIXFOCO_API_URL}/mixfoco/ml-ia/kb-produto/{item_id}",
            headers={"X-ML-IA-Secret": MIXFOCO_ML_IA_SECRET},
            timeout=10,
        )
        if not resp.ok:
            return ""
        entradas = resp.json().get("entradas", [])
    except Exception as e:
        print(f"  [WARN] Falha ao buscar KB do produto {item_id}: {e}", file=sys.stderr)
        return ""
    if not entradas:
        return ""
    return "\n".join(f"- {e.get('conteudo', '')}" for e in entradas if e.get("conteudo"))


def report_resposta(
    account_n: int,
    question_id,
    item_id: str,
    titulo_produto: str,
    pergunta: str,
    resposta: str,
    fonte: str,
    sentimento: str,
    status: str,
) -> None:
    """Report an answered/escalated/errored question to the Mixfoco app so it shows
    up in the SAC Mix IA history screen. No-op if the integration isn't configured."""
    if not (MIXFOCO_API_URL and MIXFOCO_ML_IA_SECRET):
        return
    try:
        requests.post(
            f"{MIXFOCO_API_URL}/mixfoco/ml-ia/ingest",
            json={
                "conta": account_n,
                "question_id": question_id,
                "item_id": item_id,
                "titulo_produto": titulo_produto,
                "pergunta": pergunta,
                "resposta": resposta,
                "fonte": fonte,
                "sentimento": sentimento,
                "status": status,
            },
            headers={"X-ML-IA-Secret": MIXFOCO_ML_IA_SECRET},
            timeout=10,
        )
    except Exception as e:
        print(f"  [WARN] Falha ao reportar resposta Q#{question_id} ao Mixfoco: {e}", file=sys.stderr)


# ── Claude ────────────────────────────────────────────────────────────────────

def call_claude(
    client: anthropic.Anthropic,
    question_text: str,
    item_text: str,
    guidelines: str,
    product_kb: str = "",
) -> dict:
    """
    Generate a buyer response via Claude with web search fallback.
    Returns {"response_text": str, "source": "ML"|"WEB"|"GENÉRICA"|"KB", "sentiment": str}
    """
    kb_block = f"""

---
Base de conhecimento específica deste produto (PRIORIDADE MÁXIMA — use antes de decidir ir para busca web ou resposta genérica; se a resposta vier daqui, informe FONTE: KB):
{product_kb}""" if product_kb else ""

    system = f"""Você é um especialista em atendimento ao cliente de um vendedor no Mercado Livre Brasil.
Missão: responder perguntas de compradores de forma humanizada, precisa e persuasiva para converter a venda.

{guidelines}
{kb_block}

---
Formato OBRIGATÓRIO da resposta — use exatamente esses rótulos:

SENTIMENTO: [curioso|cético|urgente|sensível_a_preço|animado]
FONTE: [ML|WEB|GENÉRICA|KB]
RESPOSTA: [texto final da resposta ao comprador]

Regras de FONTE:
- KB  → informação veio da base de conhecimento específica do produto (ver acima) — sempre prefira esta fonte quando ela responder à pergunta
- ML  → informação encontrada explicitamente nos atributos ou descrição do anúncio
- WEB → use a ferramenta de busca web disponível quando a confiança nos dados do anúncio for < 90%; se encontrar o dado, use-o e informe FONTE: WEB
- GENÉRICA → somente se nem a base de conhecimento, nem o anúncio, nem a busca web tiverem o dado; nesse caso use EXATAMENTE o texto:
  "Olá! Para mais detalhes sobre essa especificação, recomendo entrar em contato pelo chat do Mercado Livre — assim consigo te ajudar com mais precisão. 😊"

NUNCA invente especificações técnicas. NUNCA ultrapasse 2000 caracteres na RESPOSTA."""

    user = f"""Pergunta do comprador: {question_text}

Dados do anúncio:
{item_text}"""

    messages = [{"role": "user", "content": user}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 2}]

    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=system,
            tools=tools,
            messages=messages,
        )
        # Handle server-side tool loop exhaustion (rare for single-question responses)
        while response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=system,
                tools=tools,
                messages=messages,
            )
    except anthropic.APIError as e:
        print(f"  [WARN] Erro Claude API: {e}", file=sys.stderr)
        return {"response_text": GENERIC_RESPONSE, "source": "GENÉRICA", "sentiment": "curioso"}

    # Extract last text block; detect if web search was used
    final_text = ""
    web_used = False
    for block in response.content:
        block_type = getattr(block, "type", "")
        if block_type == "text":
            final_text = block.text
        elif block_type == "server_tool_use":
            web_used = True

    sentiment_m = re.search(r"SENTIMENTO:\s*(\S+)", final_text, re.IGNORECASE)
    fonte_m = re.search(r"FONTE:\s*(\S+)", final_text, re.IGNORECASE)
    resp_m = re.search(r"RESPOSTA:\s*(.+)", final_text, re.IGNORECASE | re.DOTALL)

    sentiment = sentiment_m.group(1).lower() if sentiment_m else "curioso"
    source_raw = fonte_m.group(1).upper() if fonte_m else ("WEB" if web_used else "ML")
    source = source_raw if source_raw in ("ML", "WEB", "GENÉRICA", "KB") else ("WEB" if web_used else "ML")
    response_text = resp_m.group(1).strip() if resp_m else final_text.strip()

    if not response_text or len(response_text) < 5:
        return {"response_text": GENERIC_RESPONSE, "source": "GENÉRICA", "sentiment": sentiment}

    return {"response_text": response_text, "source": source, "sentiment": sentiment}


# ── Persistence ───────────────────────────────────────────────────────────────

def append_pending(question: dict, item_id: str, reason: str, account_n: int):
    q_id = question.get("id", "?")
    q_text = question.get("text", "")
    if IN_CI:
        print(f"  [ESCALADA] Q#{q_id} — {reason} — pergunta: {q_text[:100]}")
        return
    path = os.path.join(AGENT_DIR, "pending-questions.md")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n## [{now}] Conta {account_n} — Item {item_id}\n"
        f"**Pergunta:** {q_text}\n"
        f"**Motivo escalada:** {reason}\n\n"
    )
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Perguntas Pendentes\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def write_log(entries: list, date_str: str):
    if IN_CI:
        print("\n--- Log desta execução ---")
        for e in entries:
            print(e)
        return
    log_dir = os.path.join(AGENT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{date_str}.md")
    header = f"# Log {date_str}\n\n" if not os.path.exists(log_path) else ""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(header + "\n".join(entries) + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY não configurado.", file=sys.stderr)
        sys.exit(1)

    claude = anthropic.Anthropic(api_key=api_key)
    guidelines = load_guidelines()
    date_str = datetime.now().strftime("%Y-%m-%d")

    counts = {"ml": 0, "web": 0, "kb": 0, "generica": 0, "escaladas": 0, "erros": 0, "contas": 0}
    log_entries: list[str] = []

    n = 1
    while account_exists(n):
        token = get_initial_token(n)
        if token is None:
            print(f"  Conta {n}: sem token válido. Configure ML_REFRESH_TOKEN_{n} ou ML_ACCESS_TOKEN_{n}.", file=sys.stderr)
            n += 1
            continue

        counts["contas"] += 1
        print(f"\n▶ Conta {n}")

        questions = fetch_questions(token)
        if questions is None:
            # Token expired — try refresh
            token = _do_refresh(n)
            if not token:
                print(f"  Token expirado e renovação falhou. Pulando conta {n}.", file=sys.stderr)
                n += 1
                continue
            questions = fetch_questions(token) or []

        if not questions:
            print(f"  Sem perguntas pendentes.")
            n += 1
            continue

        print(f"  {len(questions)} pergunta(s) encontrada(s).")

        for q in questions:
            q_id = q.get("id")
            item_id = q.get("item_id", "")
            q_text = q.get("text", "")
            t = datetime.now().strftime("%H:%M")

            # Fast escalation check — no Claude needed
            if is_escalation(q_text):
                append_pending(q, item_id, "tópico bloqueado", n)
                counts["escaladas"] += 1
                log_entries.append(
                    f"- [{t}] Q#{q_id} — Item {item_id} — [ESCALADA] — tópico bloqueado"
                )
                print(f"  Q#{q_id} → ESCALADA (tópico bloqueado)")
                report_resposta(n, q_id, item_id, "", q_text, "", None, None, "escalada")
                continue

            item = fetch_item(item_id, token)
            if not item:
                counts["erros"] += 1
                log_entries.append(
                    f"- [{t}] Q#{q_id} — Item {item_id} — [ERRO] — item não encontrado"
                )
                print(f"  Q#{q_id} → ERRO (item não encontrado)", file=sys.stderr)
                report_resposta(n, q_id, item_id, "", q_text, "", None, None, "erro")
                continue

            titulo_produto = item.get("title", "")
            product_kb = fetch_product_kb(item_id)
            result = call_claude(claude, q_text, item_to_text(item), guidelines, product_kb)
            response_text = result["response_text"]
            source = result["source"]
            sentiment = result["sentiment"]

            if post_answer_api(q_id, response_text, token):
                tag = f"[{source}]"
                key = source.lower() if source != "GENÉRICA" else "generica"
                counts[key] += 1
                log_entries.append(
                    f"- [{t}] Q#{q_id} — Item {item_id} — {tag} — [{sentiment}] — resposta postada"
                )
                print(f"  Q#{q_id} → {tag} ({sentiment})")
                report_resposta(
                    n, q_id, item_id, titulo_produto, q_text, response_text,
                    source, sentiment, "respondida",
                )
            else:
                counts["erros"] += 1
                log_entries.append(
                    f"- [{t}] Q#{q_id} — Item {item_id} — [ERRO] — falha ao postar"
                )
                report_resposta(
                    n, q_id, item_id, titulo_produto, q_text, response_text,
                    source, sentiment, "erro",
                )

        n += 1

    if log_entries:
        write_log(log_entries, date_str)

    print(f"""
✅ Respondidas (anúncio ML): {counts['ml']}
📚 Respondidas (base de conhecimento): {counts['kb']}
🔍 Respondidas (busca web): {counts['web']}
💬 Resposta genérica postada: {counts['generica']}
⏳ Escaladas para revisão humana: {counts['escaladas']}
❌ Erros: {counts['erros']}
📋 Contas processadas: {counts['contas']}""")


if __name__ == "__main__":
    main()
