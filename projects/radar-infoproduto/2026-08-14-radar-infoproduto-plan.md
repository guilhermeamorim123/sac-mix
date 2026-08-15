---
type: spec
subtype: plan
name: "Radar Infoproduto — Plano de Implementação"
project: "[[Radar Infoproduto]]"
owner: "[[Guilherme Figueredo]]"
date: 2026-08-14
status: pronto para execução
tags:
  - project/radar-infoproduto
---

# Radar Infoproduto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um script de linha de comando que coleta anúncios de infoproduto na UE/UK pela Meta Ad Library API, agrupa em ofertas, ranqueia por evidência de lucro e escreve uma nota markdown no vault.

**Architecture:** Entrada única em `scripts/radar_infoproduto.py` (argparse + bootstrap de venv + orquestração) sobre um pacote `scripts/radar/` de módulos pequenos. Só `meta_client.py` toca a rede; `classify`, `offers`, `store` e `render` são funções puras testadas offline com fixture.

**Tech Stack:** Python 3.9.6, `requests`, `pytest`. Venv privado em `scripts/.venv-radar/` com re-exec, seguindo o padrão de `scripts/transcrever_audio.py`.

**Spec:** `2026-08-14-radar-infoproduto-design.md` nesta mesma pasta.

---

## Convenções deste plano

- **Todo commit** termina com a linha `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`. Os comandos abaixo omitem a linha para não repetir; adicione sempre.
- Mensagem de commit em pt-BR sem acento, prefixo `feat(radar):` / `test(radar):` / `chore(radar):`, seguindo o histórico do repositório.
- **Atenção:** a regra de "sem acento" vale **só para mensagem de commit**. Toda string pt-BR que o usuário lê — `print`, `sys.exit`, texto da nota markdown — vai **com acentuação correta**, como em `scripts/transcrever_audio.py`. Copie os blocos de código deste plano literalmente; eles já estão acentuados.
- Comandos rodam da raiz do vault: `/Users/sergiogpngmail.com/Chief of Staff`.
- Depois da Task 2, o interpretador dos testes é `scripts/.venv-radar/bin/python`.
- **Nunca commitar** `projects/radar-infoproduto/data/runs/` — é cache regenerável e entra no `.gitignore` na Task 2.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---------|------------------|
| `scripts/radar_infoproduto.py` | CLI, bootstrap de venv, guarda de países, orquestração |
| `scripts/radar/config.py` | Dado puro: países, termos, listas de domínio, pesos, limiares |
| `scripts/radar/meta_client.py` | Único módulo com rede: URL, paginação, retry, rate limit |
| `scripts/radar/classify.py` | Anúncio → é infoproduto? é lusófono? Funções puras |
| `scripts/radar/offers.py` | Anúncios → ofertas agrupadas, score, portão de maturidade |
| `scripts/radar/store.py` | `history.json`: carregar, mesclar, diferenciar rodadas |
| `scripts/radar/render.py` | Ofertas + diff → markdown |
| `scripts/radar/tests/` | pytest, fixture de resposta real, zero rede |

---

## Task 1: Confirmar a API na mão antes de escrever código

Esta task não produz código. Ela existe porque três coisas do spec dependem de comportamento da API que só se confirma tocando nela: a versão corrente do Graph API, o nome exato do parâmetro de modo de busca, e quais campos voltam preenchidos para anúncio da UE. Escrever cliente antes disso é adivinhar.

**Files:** nenhum (salvar a saída em `/tmp` para virar fixture na Task 3)

- [ ] **Step 1: Obter o token**

Criar app em `developers.facebook.com`, passar pela verificação de identidade, e gerar um token de acesso com permissão de Ad Library. Exportar no shell:

```bash
export META_AD_LIBRARY_TOKEN="<token>"
```

- [ ] **Step 2: Descobrir a versão corrente do Graph API**

```bash
curl -s "https://graph.facebook.com/v99.0/me?access_token=$META_AD_LIBRARY_TOKEN" | head -20
```

Esperado: erro citando as versões suportadas. Anotar a mais alta — ela vira `API_VERSION` na Task 3.

- [ ] **Step 3: Fazer uma busca real e salvar a resposta**

Trocar `vXX.0` pela versão da Step 2:

```bash
curl -s -G "https://graph.facebook.com/vXX.0/ads_archive" \
  --data-urlencode "access_token=$META_AD_LIBRARY_TOKEN" \
  --data-urlencode "ad_type=ALL" \
  --data-urlencode "ad_reached_countries=[\"DE\",\"GB\",\"ES\"]" \
  --data-urlencode "search_terms=masterclass" \
  --data-urlencode "limit=25" \
  --data-urlencode "fields=id,page_id,page_name,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_titles,ad_delivery_start_time,ad_delivery_stop_time,ad_snapshot_url,languages,publisher_platforms,eu_total_reach,total_reach_by_location,target_locations" \
  > /tmp/radar_probe.json

python3 -c "import json;d=json.load(open('/tmp/radar_probe.json'));print(json.dumps(d,indent=2)[:3000])"
```

- [ ] **Step 4: Verificar as três incógnitas**

Confirmar na saída:

1. Existe `data` com anúncios **comerciais** (não só político). Se vier só político, a lista de países está errada — tem que ser UE/UK.
2. `eu_total_reach` vem preenchido em pelo menos parte dos anúncios.
3. `ad_creative_link_captions` vem preenchido — é o campo do qual todo o filtro depende.
4. **A forma exata de `total_reach_by_location`.** O código trata as duas possibilidades (lista de dicionários ou lista de strings), mas anote qual delas a API realmente devolve e quais chaves cada dicionário tem (`region`? `name`? `key`?). Se a forma for uma terceira, `_countries` (Task 8) precisa de um ajuste — é a única coisa neste plano escrita contra um formato não confirmado.

Testar também o modo de busca:

```bash
curl -s -G "https://graph.facebook.com/vXX.0/ads_archive" \
  --data-urlencode "access_token=$META_AD_LIBRARY_TOKEN" \
  --data-urlencode "ad_type=ALL" \
  --data-urlencode "ad_reached_countries=[\"DE\"]" \
  --data-urlencode "search_terms=free training" \
  --data-urlencode "search_type=KEYWORD_EXACT_PHRASE" \
  --data-urlencode "limit=5" \
  --data-urlencode "fields=id" | head -20
```

Se der erro de parâmetro desconhecido, anotar: `SEARCH_TYPE` fica `None` na config e a busca roda desordenada.

- [ ] **Step 5: Registrar os achados**

Anotar no arquivo do projeto (`Radar Infoproduto.md`, seção Notes): versão do Graph API, se `search_type` existe, e a proporção de anúncios com `eu_total_reach` preenchido. As Tasks 3 e 11 dependem disso.

**Sem commit** — esta task não altera o repositório.

---

## Task 2: Esqueleto do pacote, venv e pytest rodando

**Files:**
- Create: `scripts/radar/__init__.py`
- Create: `scripts/radar/tests/conftest.py`
- Create: `scripts/radar/tests/test_smoke.py`
- Create: `scripts/radar_infoproduto.py`
- Modify: `.gitignore`

- [ ] **Step 1: Criar o pacote e o conftest**

`scripts/radar/__init__.py` — arquivo vazio.

`scripts/radar/tests/conftest.py`:

```python
"""Put `scripts/` on sys.path so tests can `from radar import ...`."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
```

- [ ] **Step 2: Escrever o teste de fumaça**

`scripts/radar/tests/test_smoke.py`:

```python
def test_package_imports():
    import radar

    assert radar is not None
```

- [ ] **Step 3: Escrever a entrada com bootstrap de venv**

`scripts/radar_infoproduto.py`:

```python
#!/usr/bin/env python3
"""Radar de infoproduto em alta na UE e no Reino Unido.

Usage:
    python scripts/radar_infoproduto.py
    python scripts/radar_infoproduto.py --date 2026-08-20
    python scripts/radar_infoproduto.py --force        # ignora o cache bruto
    python scripts/radar_infoproduto.py --render-only  # re-renderiza sem gastar cota

Requer META_AD_LIBRARY_TOKEN no ambiente ou em .env na raiz do vault.
A primeira execucao cria um virtualenv privado em scripts/.venv-radar/.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
VENV = VAULT / "scripts" / ".venv-radar"
VENV_PY = VENV / "bin" / "python"

REQUIREMENTS = ["requests", "pytest"]


def ensure_venv() -> None:
    """Re-exec inside a private venv so the caller can use any python."""
    try:
        import requests  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("_RADAR_REEXEC"):
        sys.exit(
            "Erro: requests não importa nem dentro do venv.\n"
            f"Tente apagar {VENV} e rodar de novo."
        )

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.relative_to(VAULT)} (só na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        print(f"Instalando {', '.join(REQUIREMENTS)}...")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", *REQUIREMENTS],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_RADAR_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def main() -> None:
    print("Radar Infoproduto — esqueleto. A orquestração entra nas próximas tasks.")


if __name__ == "__main__":
    ensure_venv()
    main()
```

- [ ] **Step 4: Criar o venv rodando a entrada**

Run: `python3 scripts/radar_infoproduto.py`
Expected: cria o venv, instala `requests` e `pytest`, imprime a mensagem do esqueleto.

- [ ] **Step 5: Rodar o teste de fumaça**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests -v`
Expected: `test_package_imports PASSED`, 1 passed.

- [ ] **Step 6: Adicionar as exclusões ao .gitignore**

Acrescentar ao fim de `.gitignore`:

```gitignore
# Radar Infoproduto: venv privado e cache bruto da API (regeneravel)
scripts/.venv-radar/
projects/radar-infoproduto/data/runs/
```

- [ ] **Step 7: Confirmar que o venv não entra no git**

Run: `git status --short scripts/`
Expected: aparece `scripts/radar_infoproduto.py` e `scripts/radar/`, **não** aparece `scripts/.venv-radar/`.

- [ ] **Step 8: Commit**

```bash
git add scripts/radar_infoproduto.py scripts/radar/ .gitignore
git commit -m "chore(radar): esqueleto do pacote, venv privado e pytest"
```

---

## Task 3: config.py — os botões de ajuste

**Files:**
- Create: `scripts/radar/config.py`
- Create: `scripts/radar/tests/test_config.py`

- [ ] **Step 1: Escrever o teste que protege as invariantes da config**

`scripts/radar/tests/test_config.py`:

```python
from radar import config

# The API returns commercial ads ONLY for EU + UK. A stray country silently
# degrades the whole run into political-ads-only, so the list is load-bearing.
EU_PLUS_UK = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "GB",
}


def test_countries_are_eu_or_uk_only():
    assert set(config.COUNTRIES) <= EU_PLUS_UK


def test_countries_has_no_duplicates():
    assert len(config.COUNTRIES) == len(set(config.COUNTRIES))


def test_brazil_is_excluded_from_countries():
    assert "BR" not in config.COUNTRIES


def test_score_weights_sum_to_one():
    total = config.WEIGHT_LONGEVITY + config.WEIGHT_CREATIVES + config.WEIGHT_REACH
    assert abs(total - 1.0) < 1e-9


def test_domain_lists_do_not_overlap():
    assert not (config.FUNNEL_DOMAINS & config.ECOMMERCE_DOMAINS)
    assert not (config.FUNNEL_DOMAINS & config.BR_DOMAINS)
    assert not (config.ECOMMERCE_DOMAINS & config.BR_DOMAINS)


def test_search_terms_are_lowercase_and_unique():
    assert all(term == term.lower() for term in config.SEARCH_TERMS)
    assert len(config.SEARCH_TERMS) == len(set(config.SEARCH_TERMS))


def test_fields_include_every_signal_downstream_reads():
    # Dropping one of these breaks a downstream module silently — the column
    # comes back empty instead of raising. This is the guard against that.
    required = {
        "ad_creative_link_captions",  # classify: the whole domain filter
        "ad_creative_bodies",         # classify: copy match; render: promise
        "ad_delivery_start_time",     # offers: days_live
        "ad_delivery_stop_time",      # offers: active vs stopped
        "eu_total_reach",             # offers: reach
        "total_reach_by_location",    # offers: countries
        "languages",                  # classify: the lusophone label
        "page_id",                    # offers: half the identity key
        "ad_snapshot_url",            # render: creative links
    }
    assert required <= set(config.FIELDS)


def test_target_locations_is_requested_but_unread():
    # No module reads it: the lusophone label uses `languages` and the domain,
    # and the collection only ever asks for EU + UK countries, so an ad
    # targeting elsewhere never arrives. Kept in FIELDS because it costs
    # nothing and makes the cached raw.json readable by hand. Deliberately
    # NOT in `required` above — dropping it should not fail a build.
    assert "target_locations" in config.FIELDS
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_config.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.config'`

- [ ] **Step 3: Escrever a config**

`scripts/radar/config.py`:

```python
"""Tuning knobs for the radar. Pure data — no logic, no sibling imports.

This is the file to edit weekly: a term that returns nothing comes out, a new
funnel platform goes in. Everything here is covered by test_config.py, which
protects the invariants that silently break a run.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

# Confirmed by hand in Task 1. Bump when Meta deprecates it — the client
# surfaces the supported list in its error message.
API_VERSION = "v23.0"

# "KEYWORD_EXACT_PHRASE" or None. Unordered (the API default) inflates volume
# with false positives on two-word terms. Set to None if Task 1 found the
# parameter rejected.
SEARCH_TYPE = "KEYWORD_EXACT_PHRASE"

# EU 27 + UK. THE API RETURNS COMMERCIAL ADS ONLY FOR THESE. Any other country
# silently degrades the response to political ads only.
COUNTRIES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "GB",
]

# Every field a downstream module reads. Dropping one here breaks that module
# silently, with an empty column rather than an error — test_config guards it.
FIELDS = [
    "id", "page_id", "page_name",
    "ad_creative_bodies", "ad_creative_link_captions",
    "ad_creative_link_titles", "ad_creative_link_descriptions",
    "ad_delivery_start_time", "ad_delivery_stop_time",
    "ad_snapshot_url", "languages", "publisher_platforms",
    "eu_total_reach", "total_reach_by_location", "target_locations",
]

PAGE_SIZE = 100

# --------------------------------------------------------------------------
# What to look for
# --------------------------------------------------------------------------

# English only in v1: it covers the UK, Ireland and most European digital
# marketing. Each extra language multiplies the quota consumed.
SEARCH_TERMS = [
    "masterclass",
    "free training",
    "free webinar",
    "online course",
    "digital course",
    "coaching program",
    "mentorship",
    "bootcamp",
    "cohort",
    "certification",
    "join the challenge",
    "free guide",
    "playbook",
    "templates",
    "private community",
    "side hustle",
]

# Landing on one of these is near-proof of an infoproduct.
# Boundary cases kept deliberately: gumroad, whop and stan.store also host
# plain digital goods, but their volume is overwhelmingly info — course,
# template, ebook, community. Treated as funnel on purpose.
FUNNEL_DOMAINS = frozenset({
    "kajabi", "clickfunnels", "teachable", "thinkific", "learnworlds",
    "systeme.io", "kartra", "whop", "skool", "thrivecart", "samcart",
    "podia", "circle.so", "mightynetworks", "gumroad", "stan.store",
    "everwebinar", "webinarjam", "demio", "msgsndr",
})

# Landing on one of these means it is a store, not an infoproduct.
# General website builders (squarespace, wix) are deliberately NOT here: a solo
# coach running a whole funnel on one is exactly who this radar is looking for,
# and listing them would exclude that person outright. They fall through to the
# copy-based rule instead, which is the correct, weaker claim.
ECOMMERCE_DOMAINS = frozenset({
    "shopify", "myshopify", "amazon", "etsy", "ebay", "woocommerce",
    "bigcartel", "shopee", "aliexpress",
})

# Brazilian infoproduct platforms — excluded by owner decision.
BR_DOMAINS = frozenset({
    "hotmart", "eduzz", "kiwify", "braip", "monetizze", "ticto",
    "perfectpay", "cakto", "greenn", "herospark",
})

BR_LANGUAGES = frozenset({"pt", "pt_BR", "pt-BR"})
BR_COUNTRY = "BR"

# --------------------------------------------------------------------------
# Score
# --------------------------------------------------------------------------

# Longevity leads because it is the only one of the three that is hard to
# fake: nobody burns media budget for months at a loss. Reach and creative
# count confirm the size of the operation, they do not prove it works.
WEIGHT_LONGEVITY = 0.5
WEIGHT_CREATIVES = 0.3
WEIGHT_REACH = 0.2

# Caps: past these, more stops meaning more. Note the two kinds differ —
# LONGEVITY_CAP_DAYS is a hard linear clamp (min(days, cap) / cap), while
# CREATIVES_CAP and REACH_CAP are log10 denominators in offers._log_ratio.
# Doubling a log cap moves the score far less than doubling the linear one.
LONGEVITY_CAP_DAYS = 180
CREATIVES_CAP = 50
REACH_CAP = 1_000_000

# Below this, an offer may still be a test that dies next week.
MATURITY_GATE_DAYS = 21

# How many ranked offers get a full profile (copy, reach, snapshot links) in
# the run note. Past ~20 the note stops being readable in one sitting.
TOP_N_PROFILES = 20
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_config.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/config.py scripts/radar/tests/test_config.py
git commit -m "feat(radar): config de paises, termos, dominios e pesos"
```

---

## Task 4: Fixture de anúncios

Todo teste daqui pra frente lê desta fixture. Ela cobre de propósito um caso de cada armadilha: plataforma de funil, e-commerce, plataforma lusófona, idioma português, domínio próprio com e sem termo, e anúncio já encerrado.

**Files:**
- Create: `scripts/radar/tests/fixtures/ads_sample.json`
- Create: `scripts/radar/tests/test_fixture.py`

- [ ] **Step 1: Escrever a fixture**

`scripts/radar/tests/fixtures/ads_sample.json`:

```json
[
  {
    "id": "1001",
    "page_id": "500",
    "page_name": "Exemplo Academy",
    "ad_creative_bodies": ["Join the free masterclass and learn the system."],
    "ad_creative_link_captions": ["exemplo.kajabi.com"],
    "ad_delivery_start_time": "2026-03-02",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=1001",
    "languages": ["en"],
    "eu_total_reach": 300000,
    "total_reach_by_location": [{"region": "Germany", "reach": 300000}],
    "target_locations": [{"name": "Germany", "type": "country", "excluded": false}]
  },
  {
    "id": "1002",
    "page_id": "500",
    "page_name": "Exemplo Academy",
    "ad_creative_bodies": ["Last chance for the masterclass."],
    "ad_creative_link_captions": ["exemplo.kajabi.com"],
    "ad_delivery_start_time": "2026-05-10",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=1002",
    "languages": ["en"],
    "eu_total_reach": 180000,
    "total_reach_by_location": [{"region": "Spain", "reach": 180000}],
    "target_locations": [{"name": "Spain", "type": "country", "excluded": false}]
  },
  {
    "id": "1003",
    "page_id": "500",
    "page_name": "Exemplo Academy",
    "ad_creative_bodies": ["Old creative, no longer running."],
    "ad_creative_link_captions": ["exemplo.kajabi.com"],
    "ad_delivery_start_time": "2026-01-05",
    "ad_delivery_stop_time": "2026-02-01",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=1003",
    "languages": ["en"],
    "eu_total_reach": 20000,
    "target_locations": [{"name": "Germany", "type": "country", "excluded": false}]
  },
  {
    "id": "2001",
    "page_id": "600",
    "page_name": "Loja Legal",
    "ad_creative_bodies": ["Free shipping on our templates collection."],
    "ad_creative_link_captions": ["lojalegal.myshopify.com"],
    "ad_delivery_start_time": "2026-04-01",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=2001",
    "languages": ["en"],
    "eu_total_reach": 90000,
    "target_locations": [{"name": "France", "type": "country", "excluded": false}]
  },
  {
    "id": "3001",
    "page_id": "700",
    "page_name": "Curso BR",
    "ad_creative_bodies": ["Masterclass gratuita de trafego pago."],
    "ad_creative_link_captions": ["pay.hotmart.com"],
    "ad_delivery_start_time": "2026-04-15",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=3001",
    "languages": ["pt"],
    "eu_total_reach": 40000,
    "target_locations": [{"name": "Portugal", "type": "country", "excluded": false}]
  },
  {
    "id": "4001",
    "page_id": "800",
    "page_name": "Solo Coach",
    "ad_creative_bodies": ["My coaching program opens Monday."],
    "ad_creative_link_captions": ["solocoach.co.uk"],
    "ad_delivery_start_time": "2026-02-20",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=4001",
    "languages": ["en"],
    "eu_total_reach": 150000,
    "total_reach_by_location": [{"region": "United Kingdom", "reach": 150000}],
    "target_locations": [{"name": "United Kingdom", "type": "country", "excluded": false}]
  },
  {
    "id": "5001",
    "page_id": "900",
    "page_name": "Consultoria Qualquer",
    "ad_creative_bodies": ["We build custom software for logistics."],
    "ad_creative_link_captions": ["consultoria.example.com"],
    "ad_delivery_start_time": "2026-06-01",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=5001",
    "languages": ["en"],
    "eu_total_reach": 5000,
    "target_locations": [{"name": "Netherlands", "type": "country", "excluded": false}]
  },
  {
    "id": "6001",
    "page_id": "950",
    "page_name": "Nova Oferta",
    "ad_creative_bodies": ["Free training starting this week."],
    "ad_creative_link_captions": ["novaoferta.skool.com"],
    "ad_delivery_start_time": "2026-08-05",
    "ad_snapshot_url": "https://facebook.com/ads/archive/render_ad/?id=6001",
    "languages": ["en"],
    "eu_total_reach": 12000,
    "total_reach_by_location": [{"region": "Ireland", "reach": 12000}],
    "target_locations": [{"name": "Ireland", "type": "country", "excluded": false}]
  }
]
```

- [ ] **Step 2: Escrever o teste que carrega a fixture**

`scripts/radar/tests/test_fixture.py`:

```python
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def test_fixture_loads():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(ads) == 8


def test_fixture_covers_every_classification_case():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    captions = {ad["ad_creative_link_captions"][0] for ad in ads}
    assert "exemplo.kajabi.com" in captions      # funnel platform
    assert "lojalegal.myshopify.com" in captions  # e-commerce
    assert "pay.hotmart.com" in captions          # BR platform
    assert "solocoach.co.uk" in captions          # own domain + offer term
    assert "consultoria.example.com" in captions  # own domain, no offer term
    assert any("pt" in ad.get("languages", []) for ad in ads)
    assert any("ad_delivery_stop_time" in ad for ad in ads)


def test_fixture_has_one_ad_missing_reach_by_location():
    # Ad 1003 deliberately omits total_reach_by_location, so the country
    # aggregation in Task 8 is forced to tolerate the field being absent —
    # which it will be, for any ad the API has not filled in.
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    academy = [ad for ad in ads if ad["page_id"] == "500"]
    assert any("total_reach_by_location" not in ad for ad in academy)
    assert any("total_reach_by_location" in ad for ad in academy)
```

- [ ] **Step 3: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_fixture.py -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add scripts/radar/tests/fixtures/ scripts/radar/tests/test_fixture.py
git commit -m "test(radar): fixture de anuncios cobrindo os casos de classificacao"
```

---

## Task 5: classify.py — extração de domínio

**Files:**
- Create: `scripts/radar/classify.py`
- Create: `scripts/radar/tests/test_classify.py`

- [ ] **Step 1: Escrever os testes de extração e casamento**

`scripts/radar/tests/test_classify.py`:

```python
from radar import classify


def test_extract_domain_from_plain_host():
    assert classify.extract_domain({"ad_creative_link_captions": ["exemplo.kajabi.com"]}) \
        == "exemplo.kajabi.com"


def test_extract_domain_strips_scheme_path_and_www():
    ad = {"ad_creative_link_captions": ["https://WWW.Exemplo.com/promo?a=1"]}
    assert classify.extract_domain(ad) == "exemplo.com"


def test_extract_domain_strips_port_and_protocol_relative_scheme():
    port = {"ad_creative_link_captions": ["example.com:8080/path"]}
    relative = {"ad_creative_link_captions": ["//example.com/x"]}
    assert classify.extract_domain(port) == "example.com"
    assert classify.extract_domain(relative) == "example.com"


def test_extract_domain_returns_none_when_caption_missing():
    assert classify.extract_domain({}) is None
    assert classify.extract_domain({"ad_creative_link_captions": []}) is None
    assert classify.extract_domain({"ad_creative_link_captions": [""]}) is None


def test_host_matches_on_label():
    assert classify.host_matches("exemplo.kajabi.com", frozenset({"kajabi"}))


def test_host_matches_on_dotted_needle():
    assert classify.host_matches("app.systeme.io", frozenset({"systeme.io"}))


def test_host_matches_rejects_substring_of_a_label():
    # "wix" must not match "wixyzstore.com" — that is a different company.
    assert not classify.host_matches("wixyzstore.com", frozenset({"wix"}))


def test_host_matches_rejects_a_near_miss_dotted_needle():
    # The whole reason this function is not a substring check. Both of these
    # contain "systeme.io" as a substring and neither is that company. If a
    # future simplification swaps the label logic for `needle in host`, this
    # is the test that catches it.
    assert not classify.host_matches("notsysteme.io", frozenset({"systeme.io"}))
    assert not classify.host_matches("systeme.io.evil.com",
                                     frozenset({"systeme.io"}))
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_classify.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.classify'`

- [ ] **Step 3: Escrever a extração**

`scripts/radar/classify.py`:

```python
"""Decide whether an ad is an infoproduct, and whether it is Brazilian.

Pure functions over the raw ad dict the API returns. No network, no I/O.
This is the highest-leverage module in the radar: a wrong call here poisons
every downstream number.
"""

from __future__ import annotations

from typing import Any, Iterable


def extract_domain(ad: dict) -> str | None:
    """Registrable host from the ad's link caption, normalized.

    Captions arrive in several shapes: a bare host, an uppercase host, or a
    full URL with path and query. Everything is folded to a lowercase host
    with no scheme, no path, no port and no leading "www.".

    Takes the FIRST usable caption. An ad can carry several, but in this API
    they are the same link repeated across creative variants with cosmetic
    differences in case and format — not different destinations. If that ever
    stops holding, this is the assumption to revisit.
    """
    captions = ad.get("ad_creative_link_captions") or []
    for caption in captions:
        if not caption:
            continue
        host = caption.strip().lower()
        if "//" in host:
            host = host.split("//", 1)[1]
        host = host.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        if host:
            return host
    return None


def host_matches(host: str, needles: Iterable[str]) -> bool:
    """True when `host` belongs to one of `needles`.

    Matches on label boundaries, never on raw substring: "wix" matches
    "shop.wix.com" but not "wixyzstore.com".
    """
    labels = host.split(".")
    for needle in needles:
        if host == needle or host.endswith("." + needle) or needle in labels:
            return True
    return False
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_classify.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/classify.py scripts/radar/tests/test_classify.py
git commit -m "feat(radar): extracao e casamento de dominio de destino"
```

---

## Task 6: classify.py — rótulo de idioma (lusófono)

Nada é descartado por ser lusófono. Hotmart, Kiwify e as demais plataformas em
português são plataformas de funil como Kajabi — sinal **positivo** de
infoproduto. Esta task só ensina o módulo a **reconhecer** a oferta lusófona,
para que a nota possa marcá-la.

O rótulo é "lusófono" e não "brasileiro" de propósito: o idioma `pt` pega
português de Portugal também, e chamar isso de brasileiro seria errado.

**Files:**
- Modify: `scripts/radar/config.py`
- Modify: `scripts/radar/tests/test_config.py`
- Modify: `scripts/radar/classify.py`
- Modify: `scripts/radar/tests/test_classify.py`

- [ ] **Step 1: Renomear os nomes na config**

O nome `BR_DOMAINS` mentia sobre o que a lista faz agora. Em
`scripts/radar/config.py`, substituir o bloco das plataformas brasileiras e as
duas constantes seguintes por:

```python
# Portuguese-language infoproduct platforms. These are funnel platforms exactly
# like the ones above and count as POSITIVE evidence — the list exists only so
# an offer can be LABELLED lusophone, never to drop it.
PT_PLATFORM_DOMAINS = frozenset({
    "hotmart", "eduzz", "kiwify", "braip", "monetizze", "ticto",
    "perfectpay", "cakto", "greenn", "herospark",
})

# "pt" alone is what the API usually sends; the regional tags show up too.
PT_LANGUAGES = frozenset({"pt", "pt_BR", "pt-BR", "pt_PT", "pt-PT"})
```

`BR_COUNTRY` sai de vez: a regra que o usava foi removida, porque a coleta só
pede países da UE e do Reino Unido — um anúncio mirando o Brasil nunca chega.

- [ ] **Step 2: Ajustar o teste da config**

Em `scripts/radar/tests/test_config.py`, trocar as referências antigas:

```python
def test_domain_lists_do_not_overlap():
    assert not (config.FUNNEL_DOMAINS & config.ECOMMERCE_DOMAINS)
    assert not (config.FUNNEL_DOMAINS & config.PT_PLATFORM_DOMAINS)
    assert not (config.ECOMMERCE_DOMAINS & config.PT_PLATFORM_DOMAINS)
```

- [ ] **Step 3: Escrever os testes do rótulo**

Acrescentar ao fim de `scripts/radar/tests/test_classify.py`:

```python
def test_is_lusophone_by_language():
    assert classify.is_lusophone({"languages": ["pt"],
                                  "ad_creative_link_captions": ["algo.com"]})


def test_is_lusophone_by_platform_domain():
    # English copy on Hotmart is still a lusophone operation.
    assert classify.is_lusophone({"languages": ["en"],
                                  "ad_creative_link_captions": ["pay.hotmart.com"]})


def test_is_lusophone_accepts_regional_language_tags():
    for tag in ("pt_BR", "pt-BR", "pt_PT", "pt-PT"):
        assert classify.is_lusophone({"languages": [tag],
                                      "ad_creative_link_captions": ["algo.com"]})


def test_english_ad_on_a_generic_domain_is_not_lusophone():
    assert not classify.is_lusophone({"languages": ["en"],
                                      "ad_creative_link_captions": ["solocoach.co.uk"]})
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_classify.py -v`
Expected: FAIL com `AttributeError: module 'radar.classify' has no attribute 'is_lusophone'`

- [ ] **Step 5: Implementar**

Acrescentar o import no topo de `scripts/radar/classify.py`, logo abaixo de
`from typing import ...`:

```python
from radar import config
```

E acrescentar ao fim do arquivo:

```python
def is_lusophone(ad: dict) -> bool:
    """True when the offer speaks Portuguese — Brazilian or Portuguese.

    This is a LABEL, not a filter. Nothing is dropped for being lusophone; the
    run note marks it, because an offer the owner reads without friction is
    worth more to him than one he has to translate.

    Deliberately not called `is_brazilian`: the `pt` language tag covers
    Portugal too, and the platform list cannot tell a São Paulo seller from a
    Lisbon one.
    """
    if set(ad.get("languages") or []) & config.PT_LANGUAGES:
        return True
    host = extract_domain(ad)
    return bool(host and host_matches(host, config.PT_PLATFORM_DOMAINS))
```

- [ ] **Step 6: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests -v`
Expected: 24 passed (12 classify + 8 config + 3 fixture + 1 smoke).

- [ ] **Step 7: Commit**

```bash
git add scripts/radar/config.py scripts/radar/classify.py \
        scripts/radar/tests/test_config.py scripts/radar/tests/test_classify.py
git commit -m "feat(radar): rotulo lusofono no lugar da exclusao de Brasil"
```

Corpo da mensagem:

```
A decisao original excluia Brasil. Revertida pelo dono: o infoprodutor
lusofono que anuncia na Europa e a cunha de menor atrito para ele.

BR_DOMAINS vira PT_PLATFORM_DOMAINS e passa a contar como plataforma de
funil, que e o que Hotmart e Kiwify sempre foram. BR_COUNTRY sai: a coleta
so pede UE e Reino Unido, entao anuncio mirando o Brasil nunca chega.

O rotulo e "lusofono", nao "brasileiro" — o idioma pt pega Portugal tambem.
```

---

## Task 7: classify.py — identificação de infoproduto

**Files:**
- Modify: `scripts/radar/classify.py`
- Modify: `scripts/radar/tests/test_classify.py`

- [ ] **Step 1: Acrescentar os testes**

Adicionar ao fim de `scripts/radar/tests/test_classify.py`:

```python
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def load_ads():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_funnel_platform_is_infoproduct():
    ad = {"ad_creative_link_captions": ["exemplo.kajabi.com"],
          "ad_creative_bodies": ["anything at all"]}
    assert classify.is_infoproduct(ad)


def test_lusophone_platform_is_infoproduct():
    # Hotmart is one of the largest infoproduct platforms in the world. It is
    # positive evidence, not a reason to drop the ad.
    ad = {"ad_creative_link_captions": ["pay.hotmart.com"],
          "ad_creative_bodies": ["Masterclass gratuita."]}
    assert classify.is_infoproduct(ad)


def test_ecommerce_platform_is_not_infoproduct_even_with_offer_words():
    ad = {"ad_creative_link_captions": ["lojalegal.myshopify.com"],
          "ad_creative_bodies": ["Free shipping on our templates collection."]}
    assert not classify.is_infoproduct(ad)


def test_own_domain_with_offer_term_is_infoproduct():
    ad = {"ad_creative_link_captions": ["solocoach.co.uk"],
          "ad_creative_bodies": ["My coaching program opens Monday."]}
    assert classify.is_infoproduct(ad)


def test_own_domain_without_offer_term_is_not_infoproduct():
    ad = {"ad_creative_link_captions": ["consultoria.example.com"],
          "ad_creative_bodies": ["We build custom software for logistics."]}
    assert not classify.is_infoproduct(ad)


def test_offer_term_is_matched_in_link_title_too():
    ad = {"ad_creative_link_captions": ["solocoach.co.uk"],
          "ad_creative_bodies": ["Doors open."],
          "ad_creative_link_titles": ["Free training inside"]}
    assert classify.is_infoproduct(ad)


def test_ad_without_caption_is_not_infoproduct():
    assert not classify.is_infoproduct({"ad_creative_bodies": ["masterclass"]})


def test_keep_infoproducts_filters_the_fixture():
    kept = classify.keep_infoproducts(load_ads())
    kept_ids = {ad["id"] for ad in kept}
    # kajabi x3, hotmart, own-domain coach, skool. Dropped: the shopify store
    # and the software consultancy.
    assert kept_ids == {"1001", "1002", "1003", "3001", "4001", "6001"}


def test_keep_infoproducts_reports_why_it_dropped_things():
    kept, stats = classify.keep_infoproducts(load_ads(), with_stats=True)
    assert len(kept) == 6
    assert stats["not_infoproduct"] == 2  # shopify store, software consultancy
    assert stats["no_domain"] == 0
    assert stats["lusophone"] == 1        # counted, NOT dropped


def test_keep_infoproducts_never_drops_a_lusophone_ad():
    kept = classify.keep_infoproducts(load_ads())
    assert any(ad["id"] == "3001" for ad in kept)


def test_keep_infoproducts_counts_an_ad_with_no_domain():
    # The fixture has no domainless ad, so without this test the `no_domain`
    # counter is never executed and a typo in its key would pass the suite.
    # The stats dict is described as how a broken filter announces itself —
    # the announcement channel needs its own proof.
    ads = [{"id": "x", "ad_creative_bodies": ["masterclass"]}]
    kept, stats = classify.keep_infoproducts(ads, with_stats=True)
    assert kept == []
    assert stats["no_domain"] == 1
    assert stats["total"] == stats["kept"] + stats["not_infoproduct"] \
        + stats["no_domain"]


def test_generic_copy_on_an_own_domain_is_a_known_false_positive():
    # Documents the weakness rather than pretending it is not there: the bare
    # nouns in SEARCH_TERMS ("bootcamp", "templates", "certification") match
    # ordinary business copy. A gym's 6am bootcamp passes layer 2. The guard
    # against this is the manual top-20 audit, not the classifier.
    gym = {"ad_creative_link_captions": ["academia.example.com"],
           "ad_creative_bodies": ["Join our 6am bootcamp, first week free."]}
    assert classify.is_infoproduct(gym) is True


def test_multi_word_term_does_not_match_across_two_copy_fields():
    # "free training" exists in neither field on its own. Joining the fields
    # with a space would manufacture it.
    ad = {"ad_creative_link_captions": ["algo.example.com"],
          "ad_creative_bodies": ["Join the free"],
          "ad_creative_link_titles": ["training now"]}
    assert "free training" not in classify.ad_text(ad)
    assert not classify.is_infoproduct(ad)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_classify.py -v`
Expected: FAIL com `AttributeError: module 'radar.classify' has no attribute 'is_infoproduct'`

- [ ] **Step 3: Implementar**

Acrescentar ao fim de `scripts/radar/classify.py`:

```python
_TEXT_FIELDS = ("ad_creative_bodies", "ad_creative_link_titles",
                "ad_creative_link_descriptions")


def ad_text(ad: dict) -> str:
    """Every piece of copy in the ad, lowercased into one searchable blob.

    Fields are joined with a pipe, not a space, so a two-word term cannot
    match by straddling the boundary between two independent copy items —
    "Join the free" + "training now" must not read as "free training". Nine
    of the sixteen search terms are multi-word, so this is not hypothetical.
    """
    parts: list[str] = []
    for field in _TEXT_FIELDS:
        parts.extend(str(v) for v in (ad.get(field) or []))
    return " | ".join(parts).lower()


def is_infoproduct(ad: dict) -> bool:
    """Two layers: platform fingerprint first, then copy on an own domain.

    Layer 1 — the domain is a known funnel platform — is near-proof and needs
    nothing else.

    Layer 2 is weaker than it looks, and the weakness is worth stating. In
    production every ad in the corpus is here BECAUSE Meta matched one of
    these same `SEARCH_TERMS` against it at collection time, so the copy check
    is nearly always satisfied by construction. What layer 2 actually rejects
    is the narrow case of an own-domain ad with no matching copy at all —
    typically an image-only creative. The real guards on this branch are
    `ECOMMERCE_DOMAINS` and the manual top-20 audit after each run, not this
    condition.

    Splitting the terms into a broad collection list and a narrow, unambiguous
    classification list would restore genuine discrimination here. That is a
    v2 change, deliberately not made now.
    """
    host = extract_domain(ad)
    if not host:
        return False
    if host_matches(host, config.FUNNEL_DOMAINS):
        return True
    if host_matches(host, config.PT_PLATFORM_DOMAINS):
        return True
    if host_matches(host, config.ECOMMERCE_DOMAINS):
        return False
    text = ad_text(ad)
    return any(term in text for term in config.SEARCH_TERMS)


def keep_infoproducts(ads: list[dict], *, with_stats: bool = False) -> Any:
    """Filter to infoproduct ads. Nothing is dropped for language.

    With `with_stats`, also returns a counter of what happened — the run
    summary uses it, and a spike in one bucket is how a broken filter
    announces itself. `lusophone` counts ads KEPT and labelled, not dropped.
    """
    kept: list[dict] = []
    stats = {"total": len(ads), "not_infoproduct": 0, "no_domain": 0,
             "lusophone": 0}
    for ad in ads:
        if not extract_domain(ad):
            stats["no_domain"] += 1
            continue
        if not is_infoproduct(ad):
            stats["not_infoproduct"] += 1
            continue
        if is_lusophone(ad):
            stats["lusophone"] += 1
        kept.append(ad)
    stats["kept"] = len(kept)
    return (kept, stats) if with_stats else kept
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_classify.py -v`
Expected: 25 passed.

Suite inteira: 37 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/classify.py scripts/radar/tests/test_classify.py
git commit -m "feat(radar): identificacao de infoproduto por plataforma e copy"
```

---

## Task 8: offers.py — agrupar anúncios em ofertas

**Files:**
- Create: `scripts/radar/offers.py`
- Create: `scripts/radar/tests/test_offers.py`

- [ ] **Step 1: Escrever os testes**

`scripts/radar/tests/test_offers.py`:

```python
import json
from datetime import date
from pathlib import Path

from radar import classify, offers

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"
TODAY = date(2026, 8, 14)


def load_kept():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return classify.keep_infoproducts(ads)


def test_offer_key_combines_page_and_domain():
    assert offers.offer_key({"page_id": "500",
                             "ad_creative_link_captions": ["exemplo.kajabi.com"]}) \
        == "500|exemplo.kajabi.com"


def test_group_collapses_three_ads_into_one_offer():
    grouped = offers.group(load_kept(), today=TODAY)
    keys = {o["key"] for o in grouped}
    assert "500|exemplo.kajabi.com" in keys
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["total_creatives"] == 3


def test_active_creatives_excludes_stopped_ads():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["active_creatives"] == 2  # ad 1003 has a stop time


def test_days_live_uses_the_earliest_ad_start():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["earliest_ad_start"] == "2026-01-05"
    assert academy["days_live"] == (TODAY - date(2026, 1, 5)).days


def test_reach_is_summed_across_creatives():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["reach"] == 300000 + 180000 + 20000


def test_page_name_and_domain_survive_grouping():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["page_name"] == "Exemplo Academy"
    assert academy["domain"] == "exemplo.kajabi.com"


def test_lusophone_flag_is_true_when_any_ad_in_the_group_is():
    grouped = offers.group(load_kept(), today=TODAY)
    hotmart = next(o for o in grouped if o["key"] == "700|pay.hotmart.com")
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert hotmart["lusofono"] is True
    assert academy["lusofono"] is False


def test_countries_are_unioned_and_tolerate_the_field_being_absent():
    # Ad 1003 has no total_reach_by_location at all; 1001 and 1002 carry
    # Germany and Spain. The union must be both, with no crash on the third.
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["countries"] == ["Germany", "Spain"]


def test_start_time_with_timestamp_is_parsed():
    ads = [{"id": "1", "page_id": "1", "page_name": "X",
            "ad_creative_link_captions": ["x.kajabi.com"],
            "ad_delivery_start_time": "2026-07-01T10:33:00+0000"}]
    grouped = offers.group(ads, today=TODAY)
    assert grouped[0]["earliest_ad_start"] == "2026-07-01"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_offers.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.offers'`

- [ ] **Step 3: Implementar o agrupamento**

`scripts/radar/offers.py`:

```python
"""Turn ads into offers, then score them.

The API hands back ads; the unit worth analysing is the offer. One product
runs dozens of creatives, so `(page_id, domain)` is the identity key: a page
can sell more than one offer, and a domain can be run by more than one page.
"""

from __future__ import annotations

import math
from datetime import date

from radar import classify, config


def offer_key(ad: dict) -> str:
    return f"{ad.get('page_id')}|{classify.extract_domain(ad)}"


def _parse_day(value: str | None) -> date | None:
    """Accept both "2026-03-02" and "2026-03-02T10:33:00+0000"."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_int(value: object) -> int:
    """Reach arrives as int, as a numeric string, or missing."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _countries(ads: list[dict]) -> list[str]:
    """Where the offer actually reached people, from total_reach_by_location.

    Shape-tolerant on purpose: the API has shipped this as a list of dicts and
    as a list of bare strings, the dict key has been seen as `region` and as
    `name`, and the field is simply absent on ads the archive has not filled
    in. Task 1 confirms which shape is live; until then, handle all of them.
    """
    found: set[str] = set()
    for ad in ads:
        for entry in ad.get("total_reach_by_location") or []:
            if isinstance(entry, dict):
                label = entry.get("region") or entry.get("name") or entry.get("key")
            else:
                label = entry
            if label:
                found.add(str(label))
    return sorted(found)


def group(ads: list[dict], *, today: date) -> list[dict]:
    """Collapse ads into offers, aggregating the fields the score needs."""
    buckets: dict[str, list[dict]] = {}
    for ad in ads:
        buckets.setdefault(offer_key(ad), []).append(ad)

    out: list[dict] = []
    for key, group_ads in buckets.items():
        starts = [d for d in (_parse_day(a.get("ad_delivery_start_time"))
                              for a in group_ads) if d]
        earliest = min(starts) if starts else today
        active = [a for a in group_ads if not a.get("ad_delivery_stop_time")]
        bodies = sorted(
            (b for a in group_ads for b in (a.get("ad_creative_bodies") or [])),
            key=len, reverse=True,
        )
        out.append({
            "key": key,
            "page_id": str(group_ads[0].get("page_id")),
            "page_name": group_ads[0].get("page_name") or "(sem nome)",
            "domain": classify.extract_domain(group_ads[0]) or "",
            "earliest_ad_start": earliest.isoformat(),
            "days_live": (today - earliest).days,
            "active_creatives": len(active),
            "total_creatives": len(group_ads),
            "reach": sum(_as_int(a.get("eu_total_reach")) for a in group_ads),
            "countries": _countries(group_ads),
            "lusofono": any(classify.is_lusophone(a) for a in group_ads),
            "sample_copy": bodies[:3],
            "snapshot_urls": [a["ad_snapshot_url"] for a in group_ads[:5]
                              if a.get("ad_snapshot_url")],
        })
    return out
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_offers.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/offers.py scripts/radar/tests/test_offers.py
git commit -m "feat(radar): agrupamento de anuncios em ofertas"
```

---

## Task 9: offers.py — score e portão de maturidade

**Files:**
- Modify: `scripts/radar/offers.py`
- Modify: `scripts/radar/tests/test_offers.py`

- [ ] **Step 1: Acrescentar os testes**

Adicionar ao fim de `scripts/radar/tests/test_offers.py`:

```python
def make_offer(days_live, active_creatives, reach):
    return {"days_live": days_live, "active_creatives": active_creatives,
            "reach": reach}


def test_score_of_an_empty_offer_is_zero():
    assert offers.score(make_offer(0, 0, 0)) == 0.0


def test_score_of_a_maxed_offer_is_one_hundred():
    assert offers.score(make_offer(180, 50, 1_000_000)) == 100.0


def test_score_caps_do_not_reward_going_past_them():
    assert offers.score(make_offer(400, 500, 50_000_000)) == 100.0


def test_longevity_outweighs_reach_and_creatives():
    # This is the whole thesis of the radar: an old, modest offer beats a
    # loud, brand-new one. If this flips, the weights are wrong.
    old_and_small = offers.score(make_offer(180, 1, 0))
    new_and_loud = offers.score(make_offer(10, 50, 1_000_000))
    assert old_and_small > new_and_loud


def test_score_is_a_known_value():
    assert offers.score(make_offer(165, 22, 480_000)) == pytest.approx(88.69, abs=0.05)


def test_maturity_gate_splits_mature_from_emerging():
    mature, emerging = offers.partition([
        {"key": "a", "days_live": 90, "active_creatives": 5, "reach": 1000},
        {"key": "b", "days_live": 5, "active_creatives": 5, "reach": 1000},
    ])
    assert [o["key"] for o in mature] == ["a"]
    assert [o["key"] for o in emerging] == ["b"]


def test_partition_sorts_mature_by_score_descending():
    mature, _ = offers.partition([
        {"key": "low", "days_live": 30, "active_creatives": 1, "reach": 100},
        {"key": "high", "days_live": 170, "active_creatives": 40, "reach": 900_000},
    ])
    assert [o["key"] for o in mature] == ["high", "low"]
    assert mature[0]["score"] > mature[1]["score"]
```

E acrescentar `import pytest` no topo do arquivo, junto dos outros imports.

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_offers.py -v`
Expected: FAIL com `AttributeError: module 'radar.offers' has no attribute 'score'`

- [ ] **Step 3: Implementar**

Acrescentar ao fim de `scripts/radar/offers.py`:

```python
def _log_ratio(value: int, cap: int) -> float:
    """Log-normalize into 0..1. Creatives and reach both have fat tails —
    without the log, one giant offer flattens the whole ranking."""
    if value <= 0:
        return 0.0
    return min(1.0, math.log10(1 + value) / math.log10(1 + cap))


def score(offer: dict) -> float:
    """0..100. Longevity leads because it is the hardest signal to fake."""
    longevity = min(offer["days_live"], config.LONGEVITY_CAP_DAYS) / \
        config.LONGEVITY_CAP_DAYS
    longevity = max(0.0, min(1.0, longevity))
    creatives = _log_ratio(offer["active_creatives"], config.CREATIVES_CAP)
    reach = _log_ratio(offer["reach"], config.REACH_CAP)
    return round(100 * (
        config.WEIGHT_LONGEVITY * longevity
        + config.WEIGHT_CREATIVES * creatives
        + config.WEIGHT_REACH * reach
    ), 2)


def partition(all_offers: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split into (mature, emerging), scoring and sorting the mature ones.

    An offer younger than the gate may still be a test that dies next week —
    ranking it next to a 6-month survivor would be a lie.
    """
    mature: list[dict] = []
    emerging: list[dict] = []
    for offer in all_offers:
        enriched = dict(offer, score=score(offer))
        if enriched["days_live"] >= config.MATURITY_GATE_DAYS:
            mature.append(enriched)
        else:
            emerging.append(enriched)
    mature.sort(key=lambda o: o["score"], reverse=True)
    emerging.sort(key=lambda o: o["days_live"], reverse=True)
    return mature, emerging
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_offers.py -v`
Expected: 16 passed.

Se `test_score_is_a_known_value` falhar, conferir a aritmética antes de mexer no código: com os pesos 0.5/0.3/0.2 e os tetos 180/50/1.000.000, o valor esperado é `100 * (0.5*(165/180) + 0.3*log10(23)/log10(51) + 0.2*log10(480001)/log10(1000001))`.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/offers.py scripts/radar/tests/test_offers.py
git commit -m "feat(radar): score de oferta e portao de maturidade"
```

---

## Task 10: store.py — histórico e diff entre rodadas

**Files:**
- Create: `scripts/radar/store.py`
- Create: `scripts/radar/tests/test_store.py`

- [ ] **Step 1: Escrever os testes**

`scripts/radar/tests/test_store.py`:

```python
import json

from radar import store


def offer(key, score=50.0, days_live=90):
    return {"key": key, "page_id": key.split("|")[0], "page_name": f"Page {key}",
            "domain": key.split("|")[1], "days_live": days_live,
            "active_creatives": 5, "total_creatives": 6, "reach": 1000,
            "earliest_ad_start": "2026-05-01", "score": score,
            "sample_copy": [], "snapshot_urls": []}


def test_load_returns_empty_history_when_file_absent(tmp_path):
    history = store.load(tmp_path / "history.json")
    assert history["offers"] == {}
    assert history["schema_version"] == 1


def test_first_run_marks_everything_as_new(tmp_path):
    history = store.load(tmp_path / "history.json")
    diff = store.merge(history, [offer("1|a.com"), offer("2|b.com")],
                       run_date="2026-08-14")
    assert set(diff["new"]) == {"1|a.com", "2|b.com"}
    assert diff["survived"] == []
    assert diff["died"] == []


def test_second_run_separates_new_survived_and_died(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com"), offer("2|b.com")],
                run_date="2026-08-14")
    diff = store.merge(history, [offer("2|b.com"), offer("3|c.com")],
                       run_date="2026-08-21")
    assert diff["new"] == ["3|c.com"]
    assert diff["survived"] == ["2|b.com"]
    assert diff["died"] == ["1|a.com"]


def test_merge_appends_one_run_entry_per_offer(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com", score=40.0)], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com", score=60.0)], run_date="2026-08-21")
    runs = history["offers"]["1|a.com"]["runs"]
    assert [r["date"] for r in runs] == ["2026-08-14", "2026-08-21"]
    assert [r["score"] for r in runs] == [40.0, 60.0]


def test_merge_is_idempotent_for_the_same_run_date(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com", score=40.0)], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com", score=44.0)], run_date="2026-08-14")
    runs = history["offers"]["1|a.com"]["runs"]
    assert len(runs) == 1
    assert runs[0]["score"] == 44.0  # re-running the same day overwrites


def test_first_seen_is_preserved_across_runs(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com")], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com")], run_date="2026-08-21")
    entry = history["offers"]["1|a.com"]
    assert entry["first_seen_run"] == "2026-08-14"
    assert entry["last_seen_run"] == "2026-08-21"


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "history.json"
    history = store.load(path)
    store.merge(history, [offer("1|a.com")], run_date="2026-08-14")
    store.save(history, path)
    assert json.loads(path.read_text(encoding="utf-8")) == history
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_store.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.store'`

- [ ] **Step 3: Implementar**

`scripts/radar/store.py`:

```python
"""Persist offers across runs, in JSON so it travels through git.

This file is half the value of the radar. A single run shows who is
advertising today; the series shows who *survived*, and survival is the proof
of profit the whole project is after.

JSON and not SQLite on purpose: the vault moves between machines over git, and
a gitignored binary would diverge between laptop and desktop.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1

# Fields carried into the history. Copy and snapshot URLs are deliberately
# left out — they belong in the run note, and would bloat the history.
_RUN_FIELDS = ("days_live", "active_creatives", "total_creatives", "reach", "score")


def load(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "offers": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("offers", {})
    return data


def save(history: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding="utf-8")


def merge(history: dict, current: list[dict], *, run_date: str) -> dict:
    """Fold this run into the history and report what changed.

    Re-running the same date overwrites that date's entry instead of appending
    a duplicate, so a re-render or a `--force` never corrupts the series.
    """
    known = history["offers"]
    current_keys = {o["key"] for o in current}

    # "died" means: seen in the *immediately preceding* run, absent now. Offers
    # that stopped months ago must not resurface as dying every week.
    previous_run = _latest_run_before(known, run_date)
    previous_keys = {
        key for key, entry in known.items()
        if previous_run and entry.get("last_seen_run") == previous_run
    }

    diff = {"new": [], "survived": [], "died": []}

    for offer in current:
        key = offer["key"]
        entry = known.get(key)
        run_row = {"date": run_date, **{f: offer[f] for f in _RUN_FIELDS}}
        if entry is None:
            known[key] = {
                "page_id": offer["page_id"],
                "page_name": offer["page_name"],
                "domain": offer["domain"],
                "first_seen_run": run_date,
                "last_seen_run": run_date,
                "earliest_ad_start": offer["earliest_ad_start"],
                "runs": [run_row],
            }
            diff["new"].append(key)
        else:
            entry["last_seen_run"] = run_date
            entry["page_name"] = offer["page_name"]
            entry["earliest_ad_start"] = offer["earliest_ad_start"]
            entry["runs"] = [r for r in entry["runs"] if r["date"] != run_date]
            entry["runs"].append(run_row)
            entry["runs"].sort(key=lambda r: r["date"])
            diff["survived"].append(key)

    for key in previous_keys - current_keys:
        diff["died"].append(key)

    for bucket in diff.values():
        bucket.sort()
    return diff


def _latest_run_before(known: dict, run_date: str) -> str | None:
    """The most recent run date already recorded, ignoring this one."""
    dates = {entry["last_seen_run"] for entry in known.values()
             if entry.get("last_seen_run") and entry["last_seen_run"] < run_date}
    return max(dates) if dates else None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_store.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/store.py scripts/radar/tests/test_store.py
git commit -m "feat(radar): historico em JSON e diff entre rodadas"
```

---

## Task 11: render.py — a nota markdown

**Files:**
- Create: `scripts/radar/render.py`
- Create: `scripts/radar/tests/test_render.py`

- [ ] **Step 1: Escrever os testes**

`scripts/radar/tests/test_render.py`:

```python
from radar import render


def offer(key="500|exemplo.kajabi.com", score=88.69, days_live=165):
    return {"key": key, "page_id": key.split("|")[0], "page_name": "Exemplo Academy",
            "domain": key.split("|")[1], "days_live": days_live,
            "active_creatives": 22, "total_creatives": 30, "reach": 480000,
            "earliest_ad_start": "2026-03-02", "score": score,
            "countries": ["Germany", "Spain"], "lusofono": False,
            "sample_copy": ["Join the free masterclass and learn the system."],
            "snapshot_urls": ["https://facebook.com/ads/archive/render_ad/?id=1001"]}


EMPTY_DIFF = {"new": [], "survived": [], "died": []}
STATS = {"total": 100, "kept": 40, "not_infoproduct": 55, "no_domain": 5,
         "lusophone": 8}


def test_note_starts_with_valid_frontmatter():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert note.startswith("---\n")
    assert "type: radar-run\n" in note
    assert "date: 2026-08-14\n" in note
    assert "project/radar-infoproduto" in note


def test_ranking_lists_the_mature_offer():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "Exemplo Academy" in note
    assert "exemplo.kajabi.com" in note
    assert "88.69" in note


def test_profile_includes_copy_snapshot_and_countries():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "Join the free masterclass" in note
    assert "render_ad/?id=1001" in note
    assert "Germany, Spain" in note


def test_profile_renders_a_dash_when_no_country_is_known():
    blank = dict(offer(), countries=[])
    note = render.build_note([blank], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "- Países: —" in note


def test_lusophone_offer_is_marked_in_ranking_and_profile():
    pt = dict(offer(key="700|pay.hotmart.com"), lusofono=True)
    note = render.build_note([pt], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "| PT |" in note
    assert "- Idioma: lusófono" in note
    en = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                           run_date="2026-08-14")
    assert "| EN |" in en
    assert "- Idioma: inglês" in en


def test_emerging_section_appears_only_when_there_are_emerging_offers():
    without = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                                run_date="2026-08-14")
    assert "## Emergentes" not in without
    with_emerging = render.build_note(
        [offer()], [offer(key="950|novaoferta.skool.com", days_live=9)],
        EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "## Emergentes" in with_emerging
    assert "novaoferta.skool.com" in with_emerging


def test_died_section_appears_only_when_something_died():
    without = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                                run_date="2026-08-14")
    assert "## Mortas nesta rodada" not in without
    diff = {"new": [], "survived": [], "died": ["777|sumiu.kajabi.com"]}
    with_died = render.build_note([offer()], [], diff, STATS,
                                  run_date="2026-08-14")
    assert "## Mortas nesta rodada" in with_died
    assert "sumiu.kajabi.com" in with_died


def test_summary_reports_the_filter_stats():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                             run_date="2026-08-14")
    assert "100" in note   # total collected
    assert "40" in note    # kept


def test_empty_run_still_produces_a_valid_note():
    note = render.build_note([], [], EMPTY_DIFF,
                             {"total": 0, "kept": 0, "not_infoproduct": 0,
                              "no_domain": 0, "lusophone": 0},
                             run_date="2026-08-14")
    assert note.startswith("---\n")
    assert "Nenhuma oferta madura" in note


def test_write_note_creates_the_file(tmp_path):
    path = render.write_note([offer()], [], EMPTY_DIFF, STATS,
                             run_date="2026-08-14", runs_dir=tmp_path)
    assert path == tmp_path / "2026-08-14.md"
    assert path.read_text(encoding="utf-8").startswith("---\n")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_render.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.render'`

- [ ] **Step 3: Implementar**

`scripts/radar/render.py`:

```python
"""Render offers into the vault's markdown note for one run."""

from __future__ import annotations

from pathlib import Path

from radar import config


def _fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _lang(offer: dict) -> str:
    """Language marker. Lusophone offers are the low-friction ones for the
    owner to read and model, so they earn a mark of their own."""
    return "PT" if offer.get("lusofono") else "EN"


def _frontmatter(run_date: str) -> str:
    return (
        "---\n"
        "type: radar-run\n"
        f'name: "Radar Infoproduto — {run_date}"\n'
        'project: "[[Radar Infoproduto]]"\n'
        f"date: {run_date}\n"
        "tags:\n"
        "  - project/radar-infoproduto\n"
        "---\n\n"
    )


def _summary(stats: dict, mature: list[dict], emerging: list[dict],
             diff: dict) -> str:
    return (
        f"# Radar Infoproduto — rodada de {stats.get('run_date', '')}\n\n"
        "## Resumo\n\n"
        f"- Anúncios coletados: **{_fmt_int(stats['total'])}**\n"
        f"- Passaram no filtro: **{_fmt_int(stats['kept'])}**"
        f" — {_fmt_int(stats['lusophone'])} lusófonos\n"
        f"- Descartados: {_fmt_int(stats['not_infoproduct'])} não-infoproduto, "
        f"{_fmt_int(stats['no_domain'])} sem domínio\n"
        f"- Ofertas maduras: **{len(mature)}** | emergentes: {len(emerging)}\n"
        f"- Novas: {len(diff['new'])} | sobreviveram: {len(diff['survived'])} "
        f"| morreram: {len(diff['died'])}\n\n"
    )


def _ranking(mature: list[dict]) -> str:
    if not mature:
        return ("## Ranking\n\n"
                "Nenhuma oferta madura nesta rodada.\n\n")
    lines = ["## Ranking\n",
             "| # | Anunciante | Domínio | Idioma | Dias no ar | Criativos "
             "| Alcance | Score |",
             "|---|---|---|---|---|---|---|---|"]
    for i, o in enumerate(mature, start=1):
        lines.append(
            f"| {i} | {o['page_name']} | `{o['domain']}` | {_lang(o)} | "
            f"{o['days_live']} | "
            f"{o['active_creatives']}/{o['total_creatives']} | "
            f"{_fmt_int(o['reach'])} | {o['score']:.2f} |"
        )
    return "\n".join(lines) + "\n\n"


def _profiles(mature: list[dict]) -> str:
    if not mature:
        return ""
    out = [f"## Fichas — top {min(config.TOP_N_PROFILES, len(mature))}\n"]
    for i, o in enumerate(mature[:config.TOP_N_PROFILES], start=1):
        out.append(f"### {i}. {o['page_name']} — score {o['score']:.2f}\n")
        out.append(
            f"- Domínio: https://{o['domain']}\n"
            f"- No ar desde {o['earliest_ad_start']} ({o['days_live']} dias)\n"
            f"- Criativos ativos: {o['active_creatives']} de "
            f"{o['total_creatives']} totais\n"
            f"- Alcance UE: {_fmt_int(o['reach'])}\n"
            f"- Países: {', '.join(o['countries']) or '—'}\n"
            f"- Idioma: {'lusófono' if o.get('lusofono') else 'inglês'}\n"
        )
        if o["sample_copy"]:
            out.append("\n**Promessa:**\n")
            for copy in o["sample_copy"]:
                out.append(f"\n> {copy}\n")
        if o["snapshot_urls"]:
            links = " · ".join(f"[criativo {n}]({u})"
                               for n, u in enumerate(o["snapshot_urls"], start=1))
            out.append(f"\n{links}\n")
        out.append("\n")
    return "".join(out)


def _emerging(emerging: list[dict]) -> str:
    if not emerging:
        return ""
    lines = [f"## Emergentes (menos de {config.MATURITY_GATE_DAYS} dias)\n",
             "Sem ranking — podem ser teste e morrer semana que vem.\n",
             "| Anunciante | Domínio | Dias no ar | Criativos |",
             "|---|---|---|---|"]
    for o in emerging:
        lines.append(f"| {o['page_name']} | `{o['domain']}` | {o['days_live']} "
                     f"| {o['active_creatives']} |")
    return "\n".join(lines) + "\n\n"


def _died(diff: dict) -> str:
    if not diff["died"]:
        return ""
    lines = ["## Mortas nesta rodada\n",
             "Estavam na rodada anterior e sumiram. Oferta que não sustentou.\n"]
    for key in diff["died"]:
        lines.append(f"- `{key}`")
    return "\n".join(lines) + "\n\n"


def build_note(mature: list[dict], emerging: list[dict], diff: dict,
               stats: dict, *, run_date: str) -> str:
    stats = dict(stats, run_date=run_date)
    return (
        _frontmatter(run_date)
        + _summary(stats, mature, emerging, diff)
        + _ranking(mature)
        + _profiles(mature)
        + _emerging(emerging)
        + _died(diff)
        + "---\n**See also:** [[Radar Infoproduto]]\n"
    )


def write_note(mature: list[dict], emerging: list[dict], diff: dict,
               stats: dict, *, run_date: str, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run_date}.md"
    path.write_text(build_note(mature, emerging, diff, stats,
                               run_date=run_date), encoding="utf-8")
    return path
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_render.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/render.py scripts/radar/tests/test_render.py
git commit -m "feat(radar): renderizacao da nota markdown da rodada"
```

---

## Task 12: meta_client.py — o único módulo com rede

**Files:**
- Create: `scripts/radar/meta_client.py`
- Create: `scripts/radar/tests/test_meta_client.py`

- [ ] **Step 1: Escrever os testes (sem rede)**

`scripts/radar/tests/test_meta_client.py`:

```python
import pytest

from radar import meta_client


def test_build_params_serializes_countries_as_json_array():
    params = meta_client.build_params("tok", "masterclass", ["DE", "GB"])
    assert params["ad_reached_countries"] == '["DE", "GB"]'
    assert params["search_terms"] == "masterclass"
    assert params["ad_type"] == "ALL"
    assert params["access_token"] == "tok"


def test_build_params_joins_fields_with_commas():
    params = meta_client.build_params("tok", "masterclass", ["DE"])
    assert "ad_creative_link_captions" in params["fields"].split(",")
    assert "eu_total_reach" in params["fields"].split(",")


def test_build_params_omits_search_type_when_disabled():
    params = meta_client.build_params("tok", "masterclass", ["DE"],
                                      search_type=None)
    assert "search_type" not in params


def test_guard_rejects_a_non_eu_country():
    with pytest.raises(SystemExit) as exc:
        meta_client.assert_countries_supported(["DE", "US"])
    assert "US" in str(exc.value)


def test_guard_accepts_eu_and_uk():
    meta_client.assert_countries_supported(["DE", "GB", "ES"])


def test_next_page_url_is_read_from_paging_cursor():
    payload = {"data": [], "paging": {"next": "https://graph.facebook.com/next"}}
    assert meta_client.next_page(payload) == "https://graph.facebook.com/next"


def test_next_page_returns_none_at_the_end():
    assert meta_client.next_page({"data": []}) is None
    assert meta_client.next_page({"data": [], "paging": {}}) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_meta_client.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'radar.meta_client'`

- [ ] **Step 3: Implementar**

`scripts/radar/meta_client.py`:

```python
"""The only module that touches the network.

Everything else in the radar is a pure function over the dicts this returns,
which is what makes the rest testable offline.
"""

from __future__ import annotations

import json
import sys
import time

import requests

from radar import config

BASE = "https://graph.facebook.com"

# EU 27 + UK — the only countries for which the API returns commercial ads.
SUPPORTED = frozenset(config.COUNTRIES)


def assert_countries_supported(countries: list[str]) -> None:
    """Fail loudly on a country the API cannot serve commercial ads for.

    This guard exists because the failure is otherwise silent: with a non-EU
    country in the list the API returns political ads only, and the run looks
    like a bad result rather than a bad config.
    """
    bad = sorted(set(countries) - SUPPORTED)
    if bad:
        sys.exit(
            f"Erro: {', '.join(bad)} não é país da UE nem o Reino Unido.\n"
            "A Ad Library só devolve anúncio comercial para UE + UK. Com outro "
            "país na lista, a API responde só anúncio político, sem avisar.\n"
            "Corrija COUNTRIES em scripts/radar/config.py."
        )


def build_params(token: str, term: str, countries: list[str], *,
                 search_type: str | None = config.SEARCH_TYPE,
                 limit: int = config.PAGE_SIZE) -> dict:
    params = {
        "access_token": token,
        "ad_type": "ALL",
        "ad_reached_countries": json.dumps(countries),
        "search_terms": term,
        "fields": ",".join(config.FIELDS),
        "limit": str(limit),
    }
    if search_type:
        params["search_type"] = search_type
    return params


def next_page(payload: dict) -> str | None:
    return (payload.get("paging") or {}).get("next")


def _get(url: str, params: dict | None, *, attempts: int = 3) -> dict:
    """GET with exponential backoff. Raises RuntimeError when out of quota."""
    delay = 5
    for attempt in range(1, attempts + 1):
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200:
            return response.json()
        if response.status_code in (429, 500, 502, 503):
            if attempt == attempts:
                raise RuntimeError(f"quota ou instabilidade: HTTP "
                                   f"{response.status_code}")
            print(f"  HTTP {response.status_code} — nova tentativa em {delay}s")
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:400]}")
    raise RuntimeError("tentativas esgotadas")


def fetch_term(token: str, term: str, countries: list[str], *,
               max_pages: int = 10) -> list[dict]:
    """All ads for one search term, following pagination."""
    ads: list[dict] = []
    payload = _get(f"{BASE}/{config.API_VERSION}/ads_archive",
                   build_params(token, term, countries))
    ads.extend(payload.get("data") or [])
    pages = 1
    url = next_page(payload)
    while url and pages < max_pages:
        payload = _get(url, None)
        ads.extend(payload.get("data") or [])
        url = next_page(payload)
        pages += 1
    return ads


def fetch_all(token: str, terms: list[str], countries: list[str]) -> tuple[list[dict], list[str]]:
    """Every term, deduplicated by ad id.

    Returns (ads, failed_terms). A term that blows the quota does not lose the
    terms already collected — the caller caches what came back and the run
    resumes an hour later.
    """
    assert_countries_supported(countries)
    seen: set[str] = set()
    ads: list[dict] = []
    failed: list[str] = []
    for i, term in enumerate(terms, start=1):
        print(f"[{i}/{len(terms)}] '{term}'...", end=" ", flush=True)
        try:
            found = fetch_term(token, term, countries)
        except RuntimeError as exc:
            print(f"FALHOU ({exc})")
            failed.append(term)
            continue
        fresh = [ad for ad in found if ad.get("id") not in seen]
        seen.update(ad["id"] for ad in found if ad.get("id"))
        ads.extend(fresh)
        print(f"{len(found)} anúncios ({len(fresh)} novos)")
    return ads, failed
```

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_meta_client.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/radar/meta_client.py scripts/radar/tests/test_meta_client.py
git commit -m "feat(radar): cliente da Ad Library com paginacao, retry e guarda de paises"
```

---

## Task 13: Orquestração e CLI

**Files:**
- Modify: `scripts/radar_infoproduto.py`
- Create: `scripts/radar/tests/test_pipeline.py`

- [ ] **Step 1: Escrever o teste de ponta a ponta sem rede**

`scripts/radar/tests/test_pipeline.py`:

```python
import json
from datetime import date
from pathlib import Path

from radar import classify, offers, render, store

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def test_full_pipeline_from_raw_ads_to_note(tmp_path):
    """The whole chain, wired exactly as the CLI wires it, with no network."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date(2026, 8, 14))
    mature, emerging = offers.partition(grouped)

    history_path = tmp_path / "history.json"
    history = store.load(history_path)
    diff = store.merge(history, mature + emerging, run_date="2026-08-14")
    store.save(history, history_path)

    note_path = render.write_note(mature, emerging, diff, stats,
                                  run_date="2026-08-14", runs_dir=tmp_path)

    note = note_path.read_text(encoding="utf-8")
    assert "Exemplo Academy" in note        # kajabi offer ranked
    assert "Solo Coach" in note             # own-domain offer ranked
    assert "Nova Oferta" in note            # skool offer, emerging (9 days)
    assert "Curso BR" in note               # hotmart offer, kept and marked PT
    assert "Loja Legal" not in note         # e-commerce filtered out
    assert "Consultoria Qualquer" not in note  # no offer term
    assert history_path.is_file()


def test_pipeline_marks_the_lusophone_offer_without_dropping_it(tmp_path):
    """The reversal of the original Brazil exclusion, pinned end to end."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date(2026, 8, 14))
    mature, emerging = offers.partition(grouped)

    note = render.build_note(mature, emerging, {"new": [], "survived": [],
                                                "died": []},
                             stats, run_date="2026-08-14")
    assert stats["lusophone"] == 1
    assert "Curso BR" in note
    assert "| PT |" in note
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests/test_pipeline.py -v`
Expected: PASS — todos os módulos já existem. Se falhar, o erro aponta a incompatibilidade real entre eles, que é exatamente o que este teste existe para pegar.

- [ ] **Step 3: Escrever a orquestração**

Substituir a função `main()` de `scripts/radar_infoproduto.py` (e acrescentar os imports que ela usa) por:

```python
def load_token() -> str:
    """Token from the environment, falling back to .env at the vault root."""
    token = os.environ.get("META_AD_LIBRARY_TOKEN")
    if token:
        return token
    env_file = VAULT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("META_AD_LIBRARY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(
        "Erro: META_AD_LIBRARY_TOKEN não encontrado.\n"
        "Gere um token em developers.facebook.com (app com acesso à Ad Library) "
        "e exporte:\n"
        '  export META_AD_LIBRARY_TOKEN="<token>"\n'
        "Ou coloque a linha META_AD_LIBRARY_TOKEN=<token> no .env da raiz do vault."
    )


def main() -> None:
    import argparse
    from datetime import date

    sys.path.insert(0, str(VAULT / "scripts"))
    from radar import classify, config, meta_client, offers, render, store

    parser = argparse.ArgumentParser(
        description="Radar de infoproduto em alta na UE e no Reino Unido.")
    parser.add_argument("--date", help="data da rodada (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--force", action="store_true",
                        help="ignora o cache bruto e coleta de novo")
    parser.add_argument("--render-only", action="store_true",
                        help="re-renderiza a partir do cache, sem gastar cota")
    args = parser.parse_args()

    run_date = args.date or date.today().isoformat()
    base = VAULT / "projects" / "radar-infoproduto"
    raw_path = base / "data" / "runs" / run_date / "raw.json"
    history_path = base / "data" / "history.json"
    runs_dir = base / "runs"

    meta_client.assert_countries_supported(config.COUNTRIES)

    if raw_path.is_file() and not args.force:
        print(f"Usando cache de {raw_path.relative_to(VAULT)} "
              f"(--force para recoletar)")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        failed: list[str] = []
    elif args.render_only:
        sys.exit(f"Erro: --render-only exige o cache em "
                 f"{raw_path.relative_to(VAULT)}, que não existe.")
    else:
        print(f"Coletando {len(config.SEARCH_TERMS)} termos em "
              f"{len(config.COUNTRIES)} países...")
        raw, failed = meta_client.fetch_all(load_token(), config.SEARCH_TERMS,
                                            config.COUNTRIES)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        print(f"Bruto salvo em {raw_path.relative_to(VAULT)}")

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date.fromisoformat(run_date))
    mature, emerging = offers.partition(grouped)

    history = store.load(history_path)
    diff = store.merge(history, mature + emerging, run_date=run_date)
    store.save(history, history_path)

    note_path = render.write_note(mature, emerging, diff, stats,
                                  run_date=run_date, runs_dir=runs_dir)

    print(f"\n{stats['total']} anúncios, {stats['kept']} passaram no filtro")
    print(f"{len(mature)} ofertas maduras, {len(emerging)} emergentes")
    print(f"{len(diff['new'])} novas, {len(diff['survived'])} sobreviveram, "
          f"{len(diff['died'])} morreram")
    if failed:
        print(f"\nAVISO: {len(failed)} termos falharam ({', '.join(failed)}). "
              f"Rode de novo em 1h com --force para completar.")
    print(f"\nNota: {note_path.relative_to(VAULT)}")
```

E acrescentar `import json` ao bloco de imports no topo do arquivo.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `scripts/.venv-radar/bin/python -m pytest scripts/radar/tests -v`
Expected: 79 passed, 0 failed.

- [ ] **Step 5: Verificar a guarda de países na prática**

Trocar temporariamente `"GB"` por `"US"` em `config.COUNTRIES`, então:

Run: `python3 scripts/radar_infoproduto.py`
Expected: sai com a mensagem `Erro: US não é país da UE nem o Reino Unido...`

Desfazer a troca.

- [ ] **Step 6: Verificar a mensagem de token ausente**

Run: `env -u META_AD_LIBRARY_TOKEN python3 scripts/radar_infoproduto.py`
Expected: sai com as instruções de gerar o token (assumindo que não exista `.env` com a chave).

- [ ] **Step 7: Commit**

```bash
git add scripts/radar_infoproduto.py scripts/radar/tests/test_pipeline.py
git commit -m "feat(radar): orquestracao, CLI e cache resumivel"
```

---

## Task 14: Primeira rodada real e documentação

**Files:**
- Modify: `docs/reference/scripts.md`
- Modify: `projects/radar-infoproduto/Radar Infoproduto.md`

- [ ] **Step 1: Rodar de verdade**

```bash
export META_AD_LIBRARY_TOKEN="<token>"
python3 scripts/radar_infoproduto.py
```

Expected: coleta os 16 termos, imprime o progresso por termo, e escreve
`projects/radar-infoproduto/runs/<hoje>.md`.

- [ ] **Step 2: Ler a nota e auditar o top 20 na mão**

Abrir a nota gerada. Para cada uma das 20 fichas, abrir o domínio e responder: **é infoproduto de verdade?**

Se mais de 3 das 20 forem falso positivo, o filtro está frouxo.

**Cuidado com o ajuste óbvio.** `SEARCH_TERMS` serve a dois donos: é o que se
manda para a API **e** o que a camada 2 procura na copy. Tirar um termo de lá
não só afrouxa a classificação — encolhe a coleta, e a oferta boa que só
aparecia por aquele termo some junto. Prefira, nesta ordem:

1. Acrescentar o domínio ofensor a `ECOMMERCE_DOMAINS` — cirúrgico, não mexe
   na coleta
2. Acrescentar a plataforma legítima que faltou a `FUNNEL_DOMAINS`
3. Só então mexer em `SEARCH_TERMS`, sabendo que perde volume

Se o padrão de falso positivo for sempre o mesmo — substantivo genérico
(`bootcamp`, `templates`, `certification`) em domínio próprio — o conserto
certo não é nenhum dos três: é separar `SEARCH_TERMS` em `COLLECT_TERMS`
(amplo, para a API) e `CLASSIFY_TERMS` (só termos compostos e inequívocos,
para a camada 2). Isso é v2, e esta rodada é que decide se vale.

Depois:

```bash
python3 scripts/radar_infoproduto.py --render-only
```

Isso re-renderiza a partir do cache, sem gastar cota.

- [ ] **Step 3: Registrar o resultado no arquivo do projeto**

Em `projects/radar-infoproduto/Radar Infoproduto.md`, seção Notes, anotar: quantos anúncios vieram, quantos passaram, quantas ofertas maduras, e quantos falso positivos apareceram no top 20. É a linha de base para comparar a próxima rodada.

- [ ] **Step 4: Documentar o script**

Em `docs/reference/scripts.md`, acrescentar à tabela Overview:

```markdown
| `radar_infoproduto.py` | Manual (semanal) | Usuário ou Claude roda | Coleta infoprodutos em alta na UE/UK pela Meta Ad Library API e escreve a nota da rodada |
```

E uma seção em Manual Scripts, seguindo o formato das existentes: o que faz, uso, comportamento passo a passo, dependências (venv privado, `META_AD_LIBRARY_TOKEN`), e o aviso de que só funciona para UE+UK.

- [ ] **Step 5: Commit**

```bash
git add docs/reference/scripts.md "projects/radar-infoproduto/Radar Infoproduto.md" projects/radar-infoproduto/runs/ projects/radar-infoproduto/data/history.json
git commit -m "docs(radar): documenta o script e registra a primeira rodada"
```

---

## Auto-revisão do plano

**Cobertura do spec:** cada seção tem task. Fontes → Task 1. Config → Task 3.
Classificação → Tasks 5, 6, 7. Agrupamento e score → Tasks 8, 9. Histórico →
Task 10. Saída → Task 11. Cliente e erros → Task 12. Orquestração, guarda de
países e cache → Task 13. Pré-requisitos → Task 1. Auditoria do filtro (risco 3
do spec) → Task 14 Step 2.

**Fora do plano, por serem fora de escopo no spec:** coletores de ClickBank,
TikTok e Trends; cobertura dos EUA; download de landing page; idiomas além do
inglês; execução agendada.

**Consistência de nomes entre tasks:** `extract_domain`, `host_matches`,
`is_lusophone`, `ad_text`, `is_infoproduct`, `keep_infoproducts` (classify);
`offer_key`, `group`, `score`, `partition` (offers); `load`, `save`, `merge`
(store); `build_note`, `write_note` (render); `assert_countries_supported`,
`build_params`, `next_page`, `fetch_term`, `fetch_all` (meta_client). Os nomes
usados nas Tasks 13 e 14 batem com os definidos nas Tasks 5 a 12.

**Contagem de testes esperada ao fim:** 1 (smoke) + 8 (config) + 3 (fixture) +
25 (classify) + 16 (offers) + 7 (store) + 10 (render) + 7 (meta_client) + 2
(pipeline) = **79**, o número conferido na Task 13 Step 4.

**Correções feitas nas revisões:**
1. `store.merge` chamava `_latest_run_before` dentro da compreensão, uma vez
   por oferta — içado para fora, e a condição de "morta" ficou mais legível.
2. Todas as strings pt-BR estavam sem acento, por aplicação equivocada da
   convenção de mensagem de commit ao texto que o usuário lê. Corrigidas, e a
   regra ficou explícita na seção de convenções.
3. **`countries` estava prometido no spec e nunca chegava.** `FIELDS` não pedia
   `total_reach_by_location`, e `offers.group` não agregava o campo — a ficha
   sairia sem os países toda semana, sem erro nenhum. Adicionados o campo, o
   helper `_countries` tolerante a formato, a linha na ficha, e um teste em
   `test_config` que trava a lista de `FIELDS` contra remoção acidental.
4. `squarespace` e `wix` saíram de `ECOMMERCE_DOMAINS`: são construtores de
   site genéricos, e listá-los excluía justamente o coach solo que o radar
   procura. `thinkific` e `learnworlds` entraram em `FUNNEL_DOMAINS` — as duas
   são grandes na Europa e faltavam.
5. `host_matches` só tinha teste do caso positivo do domínio pontuado.
   Adicionado o negativo, que é a razão de a função existir.

**Mudança de escopo pedida pelo dono em 15/08/2026:** a exclusão de Brasil
caiu. As Tasks 6 e 7 foram reescritas — `BR_DOMAINS` virou
`PT_PLATFORM_DOMAINS` e passa a contar como plataforma de funil (que é o que
Hotmart e Kiwify sempre foram), `is_brazil` virou `is_lusophone` e serve só de
rótulo, e `BR_COUNTRY` saiu junto com a regra de `target_locations` que nunca
poderia disparar. A nota ganha coluna de idioma. **Isso não dá acesso ao
mercado brasileiro** — anúncio entregue no Brasil não existe no acervo
comercial da API. O que aparece é o infoprodutor lusófono anunciando na Europa.

---
**See also:** [[Radar Infoproduto]] | [[Guilherme Figueredo]]
