#!/usr/bin/env python3
"""Transcribe meeting audio into the vault using faster-whisper (local, offline).

Usage:
    python scripts/transcrever_audio.py "gravacao.m4a" <member-slug>
    python scripts/transcrever_audio.py "weekly.m4a" --type weekly
    python scripts/transcrever_audio.py "reuniao.m4a" --type project --project <slug>
    python scripts/transcrever_audio.py "audio.m4a" --type note      # quick dictation
    python scripts/transcrever_audio.py "gravacao.m4a" <slug> --date 2026-03-23

Output: `transcription.txt` in the meeting folder (plus a timestamped variant).

Transcription runs entirely on this machine — no audio leaves the vault.
The first run bootstraps a private virtualenv in `scripts/.venv-whisper/`
and downloads the model (~500 MB for `small`, cached in ~/.cache/huggingface).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
VENV = VAULT / "scripts" / ".venv-whisper"
VENV_PY = VENV / "bin" / "python"

# PyAV ships no cp39/x86_64 wheel from 14.x on; 13.1.0 is the last that does.
# Without the pin, pip tries to build from source and needs pkg-config + ffmpeg.
REQUIREMENTS = ["av==13.1.0", "faster-whisper"]

AUDIO_SUFFIXES = {".m4a", ".mp3", ".wav", ".aiff", ".aif", ".mp4", ".mov",
                  ".ogg", ".opus", ".flac", ".webm", ".aac", ".wma"}


# --------------------------------------------------------------------------
# venv bootstrap — re-exec inside the private venv so the caller can use any
# python. Guarded by an env sentinel so a broken install can't loop forever.
# --------------------------------------------------------------------------

def ensure_venv() -> None:
    try:
        import faster_whisper  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("_TRANSCREVER_REEXEC"):
        sys.exit(
            "Erro: faster-whisper não importa nem dentro do venv.\n"
            f"Tente apagar {VENV} e rodar de novo."
        )

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.relative_to(VAULT)} (só na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        print(f"Instalando {', '.join(REQUIREMENTS)} — pode levar alguns minutos...")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", *REQUIREMENTS],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_TRANSCREVER_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


# --------------------------------------------------------------------------
# Vocabulary — seeding Whisper with vault proper nouns is what makes the
# difference between "Mix Conecta" and "nomics conecta".
# --------------------------------------------------------------------------

def collect_vocabulary(limit: int = 40) -> list[str]:
    names: list[str] = []

    for folder in ("team", "people"):
        for path in sorted((VAULT / folder).glob("*/*.md")) if folder == "team" \
                else sorted((VAULT / folder).glob("*.md")):
            stem = path.stem
            if stem.lower() in {"readme", "index"} or "dev-plan" in stem:
                continue
            names.append(stem)

    for folder in ("projects", "companies"):
        base = VAULT / folder
        if base.is_dir():
            names.extend(p.name for p in sorted(base.iterdir()) if p.is_dir())
            names.extend(p.stem for p in sorted(base.glob("*.md")))

    # Project memories carry the display names that matter most in meetings.
    for path in sorted((VAULT / "memory").glob("project_*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")[:400]
        match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if match:
            head = re.split(r"[—\-–:,]", match.group(1).strip())[0].strip()
            if 2 < len(head) < 40:
                names.append(head)

    seen, out = set(), []
    for name in names:
        key = name.lower()
        if key not in seen and len(name) > 2:
            seen.add(key)
            out.append(name)
    return out[:limit]


def build_prompt(extra: str | None) -> str:
    parts = ["Transcrição de reunião de trabalho em português do Brasil."]
    vocab = collect_vocabulary()
    if vocab:
        parts.append("Nomes próprios: " + ", ".join(vocab) + ".")
    if extra:
        parts.append(extra.strip().rstrip(".") + ".")
    prompt = " ".join(parts)
    # Whisper truncates initial_prompt around 224 tokens; stay well under.
    return prompt[:900]


# --------------------------------------------------------------------------
# Destination
# --------------------------------------------------------------------------

def resolve_destination(args, audio: Path) -> Path:
    if args.type == "note":
        return audio.parent

    day = args.date or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        sys.exit(f"Erro: --date deve ser YYYY-MM-DD, recebi '{day}'.")

    if args.type == "weekly":
        return VAULT / "weeklys" / day
    if args.type == "project":
        if not args.project:
            sys.exit("Erro: --type project exige --project <slug>.")
        return VAULT / "projects" / args.project / "meetings" / day
    if not args.member:
        sys.exit("Erro: informe o slug do membro, ou use --type weekly/project/note.")
    return VAULT / "team" / args.member / "meetings" / day


# --------------------------------------------------------------------------

def format_timestamp(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def display(path: Path) -> str:
    """Vault-relative when possible — `--type note` may write outside it."""
    try:
        return str(path.relative_to(VAULT))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcreve áudio de reunião para dentro do vault.")
    parser.add_argument("audio", help="arquivo de áudio")
    parser.add_argument("member", nargs="?", help="slug do membro (reuniões 1:1)")
    parser.add_argument("--type", choices=["1on1", "weekly", "project", "note"],
                        default="1on1")
    parser.add_argument("--project", help="slug do projeto (com --type project)")
    parser.add_argument("--date", help="data da reunião (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--model", default=os.environ.get("WHISPER_MODEL", "small"),
                        help="tiny|base|small|medium|large-v3 (padrão: small)")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--prompt", help="vocabulário extra (siglas, nomes)")
    parser.add_argument("--keep-original", action="store_true",
                        help="não mover o áudio para a pasta da reunião")
    args = parser.parse_args()

    audio = Path(args.audio).expanduser().resolve()
    if not audio.is_file():
        sys.exit(f"Erro: áudio não encontrado: {audio}")
    if audio.suffix.lower() not in AUDIO_SUFFIXES:
        print(f"Aviso: extensão '{audio.suffix}' incomum — tentando mesmo assim.")

    dest = resolve_destination(args, audio)
    dest.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel

    print(f"Modelo: {args.model} (primeira execução baixa o modelo)")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"Transcrevendo {audio.name}...")
    started = time.time()
    segments, info = model.transcribe(
        str(audio),
        language=args.language,
        vad_filter=True,               # corta silêncio: mais rápido e sem alucinação
        initial_prompt=build_prompt(args.prompt),
        beam_size=5,
    )

    total = info.duration or 0
    plain, stamped = [], []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        plain.append(text)
        stamped.append(f"[{format_timestamp(segment.start)}] {text}")
        if total:
            pct = min(100, segment.end / total * 100)
            print(f"\r  {pct:5.1f}%  ({format_timestamp(segment.end)}"
                  f" / {format_timestamp(total)})", end="", flush=True)
    print()

    if not plain:
        sys.exit("Erro: nenhuma fala detectada. O áudio está mudo ou corrompido?")

    stem = audio.stem if args.type == "note" else "transcription"
    out_plain = dest / f"{stem}.txt"
    out_stamped = dest / f"{stem}-timestamped.txt"
    out_plain.write_text("\n".join(plain) + "\n", encoding="utf-8")
    out_stamped.write_text("\n".join(stamped) + "\n", encoding="utf-8")

    if args.type != "note" and not args.keep_original:
        target = dest / f"original{audio.suffix.lower()}"
        shutil.move(str(audio), str(target))
        print(f"Áudio movido para {display(target)}")

    elapsed = time.time() - started
    words = sum(len(s.split()) for s in plain)
    print(f"\nOK — {words} palavras, {format_timestamp(total)} de áudio "
          f"em {elapsed:.0f}s ({total / elapsed:.1f}x tempo real)")
    print(f"Transcrição: {display(out_plain)}")
    print(f"Com marcação de tempo: {display(out_stamped)}")


if __name__ == "__main__":
    ensure_venv()
    main()
