#!/usr/bin/env python3
"""
Comparative realism analysis of candidate programmes for Montpellier 2026 municipal elections.

Reads scraped output files and builds a structured prompt (or full LLM analysis) comparing
each candidate's programme across multiple criteria:
  - Budgetary feasibility (vs. actual city/metropole budget)
  - Alignment with real municipal and metropolitan competencies
  - Implementation realism within a 6-year mandate
  - Internal coherence of the programme
  - Evidence-based effectiveness of proposed measures

Usage:
    # Generate a ready-to-use LLM prompt file (no API key required)
    python analyze.py

    # Generate a prompt AND call the OpenAI API for a direct analysis
    python analyze.py --api-key sk-...

    # Customise paths
    python analyze.py --output-dir data --output-file my_analysis.md

Options:
    --output-dir OUTPUT_DIR   Directory containing scraped txt files (default: ./output)
    --output-file OUTPUT_FILE Path for the generated prompt / analysis (default: analysis_prompt.md)
    --api-key API_KEY         OpenAI API key; when provided the script calls the API and appends
                              the LLM response to the output file
    --model MODEL             OpenAI model to use (default: gpt-4o)
    --max-tokens MAX_TOKENS   Maximum tokens for the LLM response (default: 4096)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Candidate definitions
# ---------------------------------------------------------------------------

CANDIDATES: list[dict[str, str]] = [
    {
        "id": "michael-delafosse",
        "name": "Michaël Delafosse",
        "list": "Demain Montpellier",
        "file_prefix": "listes_michael-delafosse",
    },
    {
        "id": "nathalie-oziol",
        "name": "Nathalie Oziol",
        "list": "Faire mieux pour Montpellier",
        "file_prefix": "listes_la-france-insoumise",
    },
    {
        "id": "jean-louis-roumegas",
        "name": "Jean-Louis Roumégas",
        "list": "Printemps montpelliérain",
        "file_prefix": "listes_les-ecologistes",
    },
    {
        "id": "isabelle-perrein",
        "name": "Isabelle Perrein",
        "list": "Aimer Montpellier",
        "file_prefix": "listes_aimer-montpellier",
    },
    {
        "id": "philippe-saurel",
        "name": "Philippe Saurel",
        "list": "Philippe Saurel",
        "file_prefix": "listes_philippe-saurel",
    },
    {
        "id": "mohed-altrad",
        "name": "Mohed Altrad",
        "list": "Mohed Altrad",
        "file_prefix": "listes_mohed-altrad",
    },
    {
        "id": "remi-gaillard",
        "name": "Rémi Gaillard",
        "list": "N'importe qui",
        "file_prefix": "listes_remi-gaillard",
    },
    {
        "id": "kadija-zbairi",
        "name": "Kadija Zbairi",
        "list": "La Municipaliste",
        "file_prefix": "listes_la-municipaliste-kadija-zbairi",
    },
    {
        "id": "morgane-lachiver",
        "name": "Morgane Lachiver",
        "list": "Lutte Ouvrière",
        "file_prefix": "listes_lutte-ouvriere",
    },
    {
        "id": "max-muller",
        "name": "Max Muller",
        "list": "Révolution Permanente",
        "file_prefix": "listes_revolution-permanente",
    },
]

# Context files included verbatim in the prompt
CONTEXT_FILE_NAMES: list[str] = [
    "role-mairie-metropole.txt",
    "budget_montpellier_2025.txt",
    "budget_montpellier-metropole_2025.txt",
    "comparateur_positionnement.txt",
]

# Maximum number of characters to include per file to keep the prompt manageable
MAX_CHARS_PER_CANDIDATE_FILE = 8_000
MAX_CHARS_PER_CONTEXT_FILE = 4_000


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def fix_encoding(text: str) -> str:
    """Re-encode text that was incorrectly decoded as Latin-1 instead of UTF-8.

    The scraper may save pages with garbled French characters (e.g., ``Ã©``
    instead of ``é``).  This function restores the original UTF-8 characters
    by re-encoding as Latin-1 and decoding as UTF-8.  Characters outside the
    Latin-1 range (e.g. arrow symbols) that cannot be round-tripped are kept
    via the ``replace`` error handler so the function never raises.
    """
    return text.encode("latin-1", errors="replace").decode("utf-8", errors="replace")


def read_file(path: Path) -> str:
    """Read a text file and apply encoding correction."""
    try:
        raw = path.read_text(encoding="utf-8")
        return fix_encoding(raw)
    except FileNotFoundError:
        return ""
    except OSError as exc:
        print(f"  WARNING: could not read {path}: {exc}", file=sys.stderr)
        return ""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_candidate_texts(output_dir: Path, candidate: dict[str, str]) -> str:
    """Return combined text for a candidate (main page + all programme pages)."""
    prefix = candidate["file_prefix"]
    parts: list[str] = []

    # Collect all matching files, main page first then programme sub-pages
    all_files = sorted(output_dir.glob(f"{prefix}*.txt"))

    for path in all_files:
        text = read_file(path)
        if text:
            # Truncate very long files
            if len(text) > MAX_CHARS_PER_CANDIDATE_FILE:
                text = text[:MAX_CHARS_PER_CANDIDATE_FILE] + "\n[... truncated ...]"
            parts.append(f"--- File: {path.name} ---\n{text}")

    return "\n\n".join(parts) if parts else "(no data found)"


def load_context_texts(output_dir: Path) -> dict[str, str]:
    """Load context files (budget, competencies, ideological positioning)."""
    contexts: dict[str, str] = {}
    for name in CONTEXT_FILE_NAMES:
        path = output_dir / name
        text = read_file(path)
        if text:
            if len(text) > MAX_CHARS_PER_CONTEXT_FILE:
                text = text[:MAX_CHARS_PER_CONTEXT_FILE] + "\n[... truncated ...]"
            contexts[name] = text
    return contexts


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

ANALYSIS_INSTRUCTIONS = """\
## Task

You are an expert in French local government, public finance, and policy analysis.

Based **only** on the source documents provided below, produce a **comparative realism analysis**
of each candidate's programme for the Montpellier 2026 municipal elections.

For each candidate write a section containing:

1. **Programme summary** (3–5 bullet points covering the main priorities)
2. **Realistic assessment** — evaluate the programme against the following criteria:
   - **Budgetary feasibility**: Are the spending commitments compatible with the actual
     budget of the Ville de Montpellier and/or Montpellier Méditerranée Métropole?
     Reference specific budget lines or totals when possible.
   - **Municipal/metropolitan competency**: Do the proposed measures fall within the
     legal competencies of the city council and metropolitan authority, or do they
     require state-level intervention?
   - **Implementation timeline**: Can these measures realistically be implemented
     within a single 6-year municipal mandate (2026–2032)?
   - **Internal coherence**: Are the different parts of the programme consistent
     with each other?
   - **Evidence-based effectiveness**: Where relevant, does research or existing
     experience support the effectiveness of the proposed measures?
3. **Key strengths** of the programme from a realism perspective
4. **Key weaknesses / risks** that could undermine delivery
5. **Verdict** — a single sentence summarising how realistic the programme is
   compared with the others

At the end, add a **Comparative summary table** with one row per candidate and a
rating (Très réaliste / Réaliste / Partiellement réaliste / Peu réaliste) for each
of the five criteria above, plus an overall rating.

Write the analysis in **French**.
"""


def build_prompt(output_dir: Path) -> str:
    """Assemble the full LLM analysis prompt."""
    sections: list[str] = []

    sections.append("# Analyse comparative des programmes — Municipales Montpellier 2026\n")
    sections.append(ANALYSIS_INSTRUCTIONS)

    # --- Context ---
    sections.append("\n---\n## Documents de contexte\n")
    context_texts = load_context_texts(output_dir)
    if context_texts:
        for name, text in context_texts.items():
            sections.append(f"### {name}\n\n{text}\n")
    else:
        sections.append(
            "_Aucun fichier de contexte trouvé. "
            "Lancez d'abord `python scraper.py` pour générer les fichiers dans `output/`._\n"
        )

    # --- Candidate data ---
    sections.append("\n---\n## Données par candidat\n")
    for candidate in CANDIDATES:
        cname = candidate["name"]
        clist = candidate["list"]
        sections.append(f"### {cname} — {clist}\n")
        text = load_candidate_texts(output_dir, candidate)
        sections.append(text)
        sections.append("")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Optional LLM call (OpenAI)
# ---------------------------------------------------------------------------

def call_openai(prompt: str, api_key: str, model: str, max_tokens: int) -> str:
    """Send the prompt to the OpenAI API and return the response text."""
    try:
        import openai  # type: ignore[import]
    except ImportError:
        print(
            "ERROR: the 'openai' package is not installed. "
            "Run `pip install openai` and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    print(f"Calling OpenAI API (model={model}, max_tokens={max_tokens})…")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un expert en politiques publiques locales françaises, "
                    "en finances municipales et en analyse programmatique. "
                    "Tu analyses les programmes des candidats aux élections municipales "
                    "de Montpellier 2026 avec rigueur et neutralité."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a comparative realism analysis prompt for Montpellier 2026 "
            "candidate programmes, optionally calling the OpenAI API."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing scraped txt files (default: ./output)",
    )
    parser.add_argument(
        "--output-file",
        default="analysis_prompt.md",
        help="Path for the generated prompt / analysis (default: analysis_prompt.md)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key; when provided the analysis is generated via the API",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use when --api-key is provided (default: gpt-4o)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum tokens for the LLM response (default: 4096)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    if not output_dir.exists():
        print(
            f"ERROR: output directory '{output_dir}' does not exist. "
            "Run `python scraper.py` first to generate the data.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Building analysis prompt from '{output_dir}' …")
    prompt = build_prompt(output_dir)

    output_path = Path(args.output_file)
    content_to_write = prompt

    if args.api_key:
        analysis = call_openai(
            prompt=prompt,
            api_key=args.api_key,
            model=args.model,
            max_tokens=args.max_tokens,
        )
        content_to_write = (
            prompt
            + "\n\n---\n\n# Analyse générée par LLM\n\n"
            + analysis
        )
        print("LLM analysis complete.")

    output_path.write_text(content_to_write, encoding="utf-8")
    print(f"Output written to: {output_path.resolve()}")

    if not args.api_key:
        print(
            "\nTip: the file contains a ready-to-use prompt. "
            "Paste its contents into your favourite LLM, or re-run with --api-key "
            "to have the analysis generated automatically."
        )


if __name__ == "__main__":
    main()
