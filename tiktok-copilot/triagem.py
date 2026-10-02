"""Triagem deterministica: separa o chat que precisa de IA do que nao precisa.

A maior parte do chat de uma live e emoji, "oi", "boa noite" e coracao. Isso
nao precisa de modelo nenhum para ser classificado, e mandar para a API custa
o mesmo que uma pergunta de verdade. Numa live movimentada e a diferenca entre
o preco fechar e nao fechar.

**Nao e descarte, e triagem.** A mensagem continua sendo gravada e continua
aparecendo no chat do painel -- ela so nao vira token. O que ela nao ganha e
sugestao de resposta, porque nao havia o que responder.

O erro caro aqui e o falso positivo: filtrar alguem que ia comprar. Por isso a
ordem das checagens e sempre a mesma -- primeiro tudo que indica interesse, e
so o que sobra pode ser considerado trivial. Na duvida, vai para a IA.
"""
from __future__ import annotations

import re
import unicodedata

from models import Analysis, ChatMessage

# --------------------------------------------------------------------------
# Sinais de interesse -- se qualquer um bater, a mensagem vai para a IA
# --------------------------------------------------------------------------

# Palavras que carregam intencao comercial. Sem acento de proposito: o texto e
# normalizado antes da comparacao, porque chat de live nao acentua.
_INTERESSE = r"""
quanto|preco|valor|custa|barato|caro|desconto|promocao|oferta|cupom
|frete|entrega|entregar|chega|prazo|envia|enviar|correio|sedex|rastreio|cep
|comprar|compra|compro|quero|queria|vou\s*levar|levo|fechar|fechado|pedido
|link|sacolinha|sacola|carrinho|site|loja
|pix|cartao|boleto|parcela|parcelar|vezes|\d+x|pagamento|pagar
|tem|temos|acabou|esgotou|esgotado|estoque|resta|restou|ultima|ultimas|reposicao|repor
|tamanho|numero|numeracao|veste|serve|cor|cores|modelo|marca|material|tecido
|garantia|troca|trocar|devolucao|devolver|defeito|nota\s*fiscal|nf
|whats|whatsapp|zap|chama|chamar|contato|telefone
|como|onde|qual|quais|quando|quanto|porque|por\s*que|pq
|funciona|serve|vale|recomenda|indica|diferenca|melhor
|reclama|problema|demora|demorou|nao\s*chegou|cade|golpe|enganad
"""
_INTERESSE_RE = re.compile(_INTERESSE.replace("\n", ""), re.IGNORECASE)

# Numero de celular: o `models.extract_whatsapp` ja captura, mas quem larga o
# numero no chat e lead quente -- nunca e trivial.
_TEM_DIGITOS_RE = re.compile(r"\d{4,}")

# --------------------------------------------------------------------------
# Sinais de trivialidade -- so valem depois que nenhum sinal de interesse bateu
# --------------------------------------------------------------------------

_SAUDACOES = frozenset("""
oi ola ola! opa eai eae ei hey hi alo alo!
bom boa dia tarde noite bomdia boatarde boanoite
tudo bem tudobem blz beleza suave firmeza
tchau ate flw falou vlw valeu obrigado obrigada obg brigado brigada
sim nao ss nn ok okay ta tah certo isso exato exatamente
kkk kkkk kkkkk kk rs rsrs haha hahaha ashuahs
top topzera show showw legal massa maneiro daora bacana
lindo linda lindao lindona amei adorei amo perfeito perfeita otimo otima
bom boa bonito bonita maravilhoso maravilhosa incrivel demais
parabens sucesso deus abencoe amem forca vamos bora simbora
primeira vez aqui novo nova aqui presente presenca cheguei voltei
oiii oieee eita nossa uau aff caramba
""".split())

# Mensagem so com emoji, pontuacao ou espaco.
_SEM_LETRA_RE = re.compile(r"^[^\w]*$", re.UNICODE)

# Repeticao de uma letra so: "kkkkkkk", "aaaaa", "eeee"
_UMA_LETRA_RE = re.compile(r"^(.)\1*$")

TAMANHO_MINIMO = 3          # abaixo disso nao ha o que classificar
MAX_PALAVRAS_TRIVIAL = 4    # acima disso a pessoa escreveu algo, mande para a IA


def _normalizar(texto: str) -> str:
    """Minusculas, sem acento, sem pontuacao nas bordas."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return sem_acento.strip()


class Triagem:
    """Decide, sem chamar a API, se uma mensagem precisa de IA.

    Recebe os nomes dos produtos do catalogo: quem cita um produto esta
    olhando para a vitrine, mesmo que nao tenha feito pergunta.
    """

    def __init__(self, catalogo=None):
        produtos = getattr(catalogo, "produtos", []) or []
        termos = set()
        for p in produtos:
            for palavra in _normalizar(str(p.get("nome", ""))).split():
                # Palavras curtas ("de", "10w") dariam falso positivo demais.
                if len(palavra) >= 4:
                    termos.add(palavra)
        self._produtos = frozenset(termos)
        self.filtradas = 0
        self.analisadas = 0

    # -- decisao -----------------------------------------------------------

    def trivial(self, msg: ChatMessage) -> bool:
        texto = _normalizar(msg.text)

        if not texto:
            return True

        # 1. Interesse explicito vence tudo o que vem depois.
        if "?" in msg.text:
            return False
        if _TEM_DIGITOS_RE.search(msg.text):
            return False
        if _INTERESSE_RE.search(texto):
            return False
        if self._produtos and self._produtos & set(texto.split()):
            return False

        # 2. Sem nenhum sinal de interesse: da para descartar por forma?
        if len(texto) < TAMANHO_MINIMO:
            return True
        if _SEM_LETRA_RE.match(texto):      # so emoji/pontuacao
            return True
        if _UMA_LETRA_RE.match(texto):      # "kkkkkkk", "aaaaa"
            return True

        palavras = texto.replace("!", " ").replace(".", " ").replace(",", " ").split()
        if not palavras:
            return True
        if len(palavras) > MAX_PALAVRAS_TRIVIAL:
            return False
        # Saudacao/reacao: TODAS as palavras precisam estar na lista. Uma
        # palavra desconhecida no meio ja e motivo para mandar para a IA.
        return all(p in _SAUDACOES for p in palavras)

    def separar(self, lote: list[ChatMessage]) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """Devolve (para_ia, triviais) e atualiza os contadores da sessao."""
        para_ia, triviais = [], []
        for msg in lote:
            (triviais if self.trivial(msg) else para_ia).append(msg)
        self.filtradas += len(triviais)
        self.analisadas += len(para_ia)
        return para_ia, triviais

    @property
    def taxa_filtrada(self) -> float:
        """% do chat que nao custou token. E o numero que valida a estimativa."""
        total = self.filtradas + self.analisadas
        return (self.filtradas / total * 100) if total else 0.0


def analise_local(msg: ChatMessage) -> Analysis:
    """Analise de uma mensagem trivial, montada sem chamar a API.

    `suggested_reply` fica vazia de proposito: nao ha o que sugerir, e o painel
    usa isso para manter a mensagem fora da fila de resposta.
    """
    return Analysis(
        message_id=msg.message_id,
        intent="elogio" if _elogio(msg.text) else "outro",
        lead_score=0,
        suggested_reply="",
        requires_human=False,
        reasoning="triagem local (sem sinal de interesse)",
    )


_ELOGIOS = frozenset("""
top topzera show showw legal massa maneiro daora bacana perfeito perfeita
lindo linda lindao lindona amei adorei amo otimo otima bonito bonita
maravilhoso maravilhosa incrivel demais parabens sucesso arrasou
""".split())


def _elogio(texto: str) -> bool:
    return bool(_ELOGIOS & set(_normalizar(texto).split()))
