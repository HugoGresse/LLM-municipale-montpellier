# LLM-municipale-montpellier

Scraper to collect all text content from [montpellier-municipales.fr](https://montpellier-municipales.fr/) into multiple txt files, for use with LLMs.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scraper.py
```

This will crawl all pages on `montpellier-municipales.fr` and save each page's text content as a separate `.txt` file in the `output/` directory.

### Options

| Option | Default | Description |
|---|---|---|
| `--output-dir` | `output` | Directory to save the txt files |
| `--delay` | `1.0` | Delay in seconds between HTTP requests |

### Example

```bash
# Save to a custom directory with a 0.5s delay between requests
python scraper.py --output-dir data --delay 0.5
```

## Output

Each page is saved as a separate `.txt` file. The filename is derived from the page URL path (e.g., `programme_logement.txt`). Each file contains:

- The page URL
- The page title
- The meta description (if present)
- The main text content of the page