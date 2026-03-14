# LLM-municipale-montpellier

Scraper to collect all text content from [montpellier-municipales.fr](https://montpellier-municipales.fr/) into multiple txt files, for use with LLMs.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### 1. Scrape the website

```bash
python scraper.py
```

This will crawl all pages on `montpellier-municipales.fr` and save each page's text content as a separate `.txt` file in the `output/` directory.

#### Options

| Option | Default | Description |
|---|---|---|
| `--output-dir` | `output` | Directory to save the txt files |
| `--delay` | `1.0` | Delay in seconds between HTTP requests |

#### Example

```bash
# Save to a custom directory with a 0.5s delay between requests
python scraper.py --output-dir data --delay 0.5
```

### 2. Analyse candidate programmes (realism comparison)

```bash
python analyze.py
```

This reads the scraped `output/` files and generates a structured LLM prompt
(`analysis_prompt.md`) comparing the realism of each candidate's programme across
multiple criteria:

- **Budgetary feasibility** — are the proposals compatible with the actual city/metropole budget?
- **Municipal competency** — do the measures fall within the city council's legal powers?
- **Implementation timeline** — can the programme be delivered in a 6-year mandate?
- **Internal coherence** — are the different parts of the programme consistent?
- **Evidence-based effectiveness** — does research support the proposed measures?

Paste the generated `analysis_prompt.md` into your favourite LLM, or let
`analyze.py` call the OpenAI API directly:

```bash
python analyze.py --api-key sk-...
```

#### Options

| Option | Default | Description |
|---|---|---|
| `--output-dir` | `output` | Directory containing scraped txt files |
| `--output-file` | `analysis_prompt.md` | Output file for the prompt / analysis |
| `--api-key` | *(none)* | OpenAI API key — when provided the LLM analysis is generated automatically |
| `--model` | `gpt-4o` | OpenAI model to use (requires `--api-key`) |
| `--max-tokens` | `4096` | Maximum tokens for the LLM response |

> **Note:** The `openai` package is only required when `--api-key` is used.
> Install it with `pip install openai`.

## Output

Each scraped page is saved as a separate `.txt` file. The filename is derived from the page URL path (e.g., `programme_logement.txt`). Each file contains:

- The page URL
- The page title
- The meta description (if present)
- The main text content of the page