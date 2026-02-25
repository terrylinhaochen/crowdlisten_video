# Content Repurposing Pipeline

This pipeline turns a source URL or local file into reusable, platform-specific drafts and prompts.
It lives entirely inside this repo and writes outputs under `content_gen/`.

## Folder structure

```
content_gen/
  sources/
    <slug>/
      source.html|source.md
      images/
        image_001.*
  processing/
    <slug>/
      extracted.txt
      manifest.json
  <slug>/
    <version>/
      <platform>/
        prompt.txt
        draft.md
```

- `sources/`: raw inputs and images/diagrams
- `processing/`: extracted text + manifest for provenance
- `<slug>/<version>/<platform>/`: outputs ready for editing

## Workflow

1) Run the CLI with a source URL or local file.
2) The script downloads HTML/markdown, extracts plain text, and saves images.
3) For each platform, it writes a prompt and a draft scaffold.
4) Edit the drafts, keep the Every-style checklist, and publish.

## Every-style prompt (built-in)

Use this prompt whenever writing or editing drafts:

```
You are writing in the Every house style.

Requirements:
- Clear thesis in the first 2-3 sentences.
- Plainspoken, human voice. No jargon without a short explanation.
- Concrete examples and specific nouns.
- Short, varied sentences. Avoid robotic cadence.
- Avoid marketing fluff, formulaic transitions, and vague "this/that".
- Minimize hedging (e.g., "might", "could", "perhaps") unless needed.

Deliverable:
- A draft tailored to the target platform.
- Use the source text as the only factual basis.
```

## AI-tells checklist

Use this checklist before finalizing any draft:

- No vague this/that without a noun
- No marketing fluff or empty superlatives
- No formulaic transitions (e.g., "In conclusion", "Additionally")
- Limited hedging unless uncertainty is real
- Avoid robotic or symmetrical sentence patterns
- Prefer concrete examples over abstractions

## CLI usage

```
python scripts/content_gen.py \
  --url "https://example.com/article" \
  --platforms "blog,linkedin,newsletter" \
  --style every \
  --version v1
```

Local file:

```
python scripts/content_gen.py --input ./notes/source.md --platforms "thread" --style every
```

## Sample config

`content_gen/sample_config.json`:

```
{
  "url": "https://example.com/article",
  "platforms": ["blog", "linkedin", "newsletter"],
  "style": "every",
  "version": "v1"
}
```

## Studio trigger

Use the Studio API to trigger the pipeline:

```
POST /api/content-gen
{
  "url": "https://example.com/article",
  "platforms": ["blog", "linkedin"],
  "style": "every",
  "version": "v1"
}
```

The response includes the output root and manifest path.
