import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const G   = "#00E676";
const G2  = "#00BFA5";
const BG  = "#07080A";
const BG2 = "#0E1014";
const W   = "#F5F7FA";
const MUT = "#6B7280";

const clamp = (v: number) => ({ extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const });

export const KeylightDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sp = (delay = 0, damping = 14) =>
    spring({ frame: frame - delay, fps, config: { damping } });

  // opacidades por cena
  const op1 = interpolate(frame, [0, 10, 72, 90],    [0, 1, 1, 0], clamp(0));
  const op2 = interpolate(frame, [90, 105, 222, 240], [0, 1, 1, 0], clamp(0));
  const op3 = interpolate(frame, [240, 255, 432, 450],[0, 1, 1, 0], clamp(0));
  const op4 = interpolate(frame, [450, 465, 730, 750],[0, 1, 1, 0], clamp(0));
  const op5 = interpolate(frame, [750, 768, 890, 900],[0, 1, 1, 0], clamp(0));

  // ── CENA 1 ─────────────────────────────────────────────────────────────────
  const s1y   = interpolate(sp(0), [0, 1], [80, 0]);
  const lineW = interpolate(frame, [15, 55],  [0, 580], clamp(0));
  const tagOp = interpolate(frame, [22, 40],  [0, 1],   clamp(0));

  // ── CENA 2 ─────────────────────────────────────────────────────────────────
  const f2  = Math.max(0, frame - 90);
  const s2y = interpolate(f2, [0, 20], [50, 0], clamp(0));
  const items = [
    { label: "Designer profissional",   sub: "R$150 por anúncio", d: 20 },
    { label: "Canva e templates",        sub: "Horas de trabalho",  d: 36 },
    { label: "Resultado inconsistente",  sub: "Perde vendas",       d: 52 },
  ];

  // ── CENA 3 ─────────────────────────────────────────────────────────────────
  const f3   = Math.max(0, frame - 240);
  const prog = interpolate(f3, [20, 180], [0, 100], clamp(0));
  const dotsCount = Math.max(0, Math.floor(f3 / 18) % 4);
  const dots = ".".repeat(dotsCount);
  const s3y  = interpolate(f3, [0, 20], [40, 0], clamp(0));

  // ── CENA 4 ─────────────────────────────────────────────────────────────────
  const f4 = Math.max(0, frame - 450);
  const cards = [
    { label: "Capa",          sub: "Fundo limpo"      },
    { label: "Uso real",      sub: "Estilo lifestyle"  },
    { label: "Hero",          sub: "Destaque total"    },
    { label: "Detalhes",      sub: "Close preciso"     },
    { label: "Diferenciais",  sub: "Por que comprar"   },
    { label: "Selos",         sub: "Confiança"         },
    { label: "FAQ",           sub: "Dúvidas comuns"    },
    { label: "Destaque",      sub: "Alta conversão"    },
  ];

  // ── CENA 5 ─────────────────────────────────────────────────────────────────
  const f5    = Math.max(0, frame - 750);
  const s5y   = interpolate(sp(750), [0, 1], [60, 0]);
  const pulse = 1 + Math.sin(f5 / 18) * 0.016;
  const glowN = Math.round((0.25 + Math.sin(f5 / 14) * 0.15) * 255);
  const glowHex = Math.max(0, Math.min(255, glowN)).toString(16).padStart(2, "0");

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: "'Arial Black', Arial, sans-serif", overflow: "hidden" }}>

      {/* ── CENA 1: LOGO ── */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: op1, pointerEvents: "none" }}>
        <div style={{ position: "absolute", width: 800, height: 800, borderRadius: "50%", background: `radial-gradient(circle, ${G}15 0%, transparent 70%)` }} />
        <div style={{ textAlign: "center", transform: `translateY(${s1y}px)`, position: "relative" }}>
          <div style={{ fontSize: 130, fontWeight: 900, letterSpacing: -6, lineHeight: 1, background: `linear-gradient(135deg, ${W} 40%, ${G})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            KEY<span style={{ background: `linear-gradient(135deg, ${G}, ${G2})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>LIGHT</span>
          </div>
          <div style={{ height: 3, width: lineW, background: `linear-gradient(90deg, ${G}, transparent)`, margin: "20px auto", borderRadius: 2 }} />
          <div style={{ fontSize: 36, color: MUT, letterSpacing: 3, textTransform: "uppercase", opacity: tagOp, fontFamily: "system-ui, sans-serif" }}>
            Seu anúncio vende pela foto
          </div>
        </div>
      </AbsoluteFill>

      {/* ── CENA 2: PROBLEMA ── */}
      <AbsoluteFill style={{ padding: "120px 80px", opacity: op2, pointerEvents: "none" }}>
        <div style={{ transform: `translateY(${s2y}px)` }}>
          <div style={{ fontSize: 28, color: G, letterSpacing: 3, textTransform: "uppercase", fontFamily: "system-ui, sans-serif", marginBottom: 20 }}>O problema</div>
          <div style={{ fontSize: 72, fontWeight: 900, color: W, lineHeight: 1.1, marginBottom: 60 }}>
            Foto ruim custa<br /><span style={{ color: "#FF4444" }}>caro demais.</span>
          </div>
          {items.map((item) => {
            const iop = interpolate(f2, [item.d, item.d + 16], [0, 1], clamp(0));
            const ix  = interpolate(f2, [item.d, item.d + 16], [-40, 0], clamp(0));
            return (
              <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 28, marginBottom: 32, opacity: iop, transform: `translateX(${ix}px)` }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF4444", flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 38, fontWeight: 700, color: W, fontFamily: "system-ui, sans-serif" }}>{item.label}</div>
                  <div style={{ fontSize: 28, color: MUT, fontFamily: "system-ui, sans-serif" }}>{item.sub}</div>
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* ── CENA 3: PROCESSAMENTO ── */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: op3, pointerEvents: "none" }}>
        <div style={{ textAlign: "center", width: "100%", padding: "0 80px", transform: `translateY(${s3y}px)` }}>
          <div style={{ width: 220, height: 220, margin: "0 auto 56px", background: BG2, borderRadius: 32, border: `2px solid ${G}55`, boxShadow: `0 0 80px ${G}20`, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 14 }}>
            <div style={{ width: 110, height: 110, background: "#131720", borderRadius: 16 }} />
            <div style={{ width: 80, height: 10, background: "#1a1f2e", borderRadius: 6 }} />
          </div>
          <div style={{ fontSize: 54, fontWeight: 900, color: W, marginBottom: 12 }}>IA processando{dots}</div>
          <div style={{ fontSize: 36, color: G, fontWeight: 700, fontFamily: "system-ui, sans-serif", marginBottom: 48 }}>{Math.round(prog)}% concluído</div>
          <div style={{ height: 8, background: "#1a1f2e", borderRadius: 999, width: "85%", margin: "0 auto", overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 999, background: `linear-gradient(90deg, ${G2}, ${G})`, width: `${prog}%`, boxShadow: `0 0 24px ${G}88` }} />
          </div>
          <div style={{ fontSize: 28, color: MUT, fontFamily: "system-ui, sans-serif", marginTop: 40 }}>8 imagens profissionais sendo criadas</div>
        </div>
      </AbsoluteFill>

      {/* ── CENA 4: RESULTADO ── */}
      <AbsoluteFill style={{ padding: "60px 56px", opacity: op4, pointerEvents: "none" }}>
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontSize: 26, color: G, letterSpacing: 3, textTransform: "uppercase", fontFamily: "system-ui, sans-serif" }}>Resultado</div>
          <div style={{ fontSize: 58, fontWeight: 900, color: W, lineHeight: 1.1 }}>8 imagens.<br />Prontas agora.</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {cards.map((card, i) => {
            const d   = i * 16 + 8;
            const cop = interpolate(f4, [d, d + 18], [0, 1], clamp(0));
            const csc = interpolate(f4, [d, d + 18], [0.88, 1], clamp(0));
            return (
              <div key={card.label} style={{ background: BG2, borderRadius: 20, border: `1.5px solid ${G}33`, padding: "22px 20px", transform: `scale(${csc})`, opacity: cop }}>
                <div style={{ width: "100%", height: 90, background: "linear-gradient(135deg, #131720, #1a2230)", borderRadius: 10, marginBottom: 12 }} />
                <div style={{ fontSize: 30, fontWeight: 700, color: W, fontFamily: "system-ui, sans-serif" }}>{card.label}</div>
                <div style={{ fontSize: 22, color: MUT, fontFamily: "system-ui, sans-serif", marginTop: 4 }}>{card.sub}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* ── CENA 5: CTA ── */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: op5, pointerEvents: "none" }}>
        <div style={{ position: "absolute", width: 1000, height: 1000, borderRadius: "50%", background: `radial-gradient(circle, ${G}${glowHex} 0%, transparent 65%)` }} />
        <div style={{ textAlign: "center", padding: "0 80px", transform: `translateY(${s5y}px)`, position: "relative" }}>
          <div style={{ fontSize: 28, color: G, letterSpacing: 3, textTransform: "uppercase", fontFamily: "system-ui, sans-serif", marginBottom: 20 }}>Experimente grátis</div>
          <div style={{ fontSize: 84, fontWeight: 900, color: W, lineHeight: 1, marginBottom: 20 }}>
            2 minutos.<br />
            <span style={{ background: `linear-gradient(90deg, ${G}, ${G2})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Resultado real.</span>
          </div>
          <div style={{ fontSize: 32, color: MUT, fontFamily: "system-ui, sans-serif", marginBottom: 64 }}>Sem designer. Sem template genérico.</div>
          <div style={{ display: "inline-block", background: `linear-gradient(135deg, ${G}, ${G2})`, borderRadius: 999, padding: "30px 68px", transform: `scale(${pulse})`, boxShadow: `0 0 60px ${G}55` }}>
            <div style={{ fontSize: 44, fontWeight: 900, color: BG, letterSpacing: -1 }}>keylight.com.br</div>
          </div>
        </div>
      </AbsoluteFill>

    </AbsoluteFill>
  );
};
