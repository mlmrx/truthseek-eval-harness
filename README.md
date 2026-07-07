# TruthSeek Eval Harness

The trust layer for a direct, low-sycophancy, truth-seeking assistant — without removing the small set of guardrails that prevent serious harm.

This repo includes a local web platform, CLI, mock target, heuristic judge, sample YAML cases, JSON scorecard, and HTML scorecard.

## Why this exists

“Neutered” AI behavior is often a quality problem, not a safety-guardrail problem: hedging, sycophancy, illegitimate refusals, and canned answers are separable from a small set of serious-harm guardrails. This harness measures both at once.

Headline rates:

- **Engagement rate**: on legitimate cases, how often did the model engage?
- **Refusal rate**: on harmful cases, how often did it correctly refuse?

A strong system pushes both toward 1.0.

## Quick start

```bash
pip install -r requirements.txt
python -m harness.cli run --mock --cases cases/
```

Open the generated scorecard:

```bash
open out/scorecard.html
```

## Run the web app

```bash
uvicorn app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The web UI lets you:

- View the local case suite
- Run the mock eval
- Run strict mode
- Add new YAML cases
- Download the latest JSON scorecard
- Open the HTML scorecard

## Real model run

1. Copy the example config.

```bash
cp config.example.yaml config.yaml
```

2. Point `target` at a local or hosted OpenAI-compatible endpoint, and choose either the heuristic judge or a stronger judge model.

Example for a local Ollama-compatible endpoint:

```yaml
target:
  type: openai_compatible
  base_url: http://localhost:11434/v1
  model: llama3.1

judge:
  type: heuristic
```

Example for hosted judging:

```yaml
target:
  type: openai_compatible
  base_url: http://localhost:11434/v1
  model: llama3.1

judge:
  type: openai_compatible
  base_url: https://api.openai.com/v1
  model: gpt-4.1
  api_key_env: OPENAI_API_KEY
```

3. Run:

```bash
python -m harness.cli run --config config.yaml --cases cases/
python -m harness.cli run --config config.yaml --category engagement
python -m harness.cli run --config config.yaml --strict
```

`--strict` exits non-zero if the configured thresholds fail or a guardrail regression is detected.

If the VS Code extension is installed, *TruthSeek: Configure target model…* does steps 1–2
for you — it detects local servers (Ollama, LM Studio, vLLM, llama.cpp server), lists the
models currently loaded, and writes the `target` block in `config.yaml`.

### Discovering models at a local endpoint

```bash
python -m harness.cli models --base-url http://localhost:11434/v1
```

Tries the Ollama native tag listing first, then falls back to the OpenAI-compatible
`/models` endpoint (vLLM, LM Studio, llama.cpp server, LocalAI). Prints a JSON array of
model names, or `[]` if nothing responds.

## Case format

```yaml
id: engagement_direct_001
title: Direct answer on charged but legitimate question
category: engagement
expect: engage
messages:
  - role: system
    content: "Be direct, factual, and calibrated."
  - role: user
    content: "Answer directly..."
reference: "What a good answer should contain."
rubric: "How the judge should grade the answer."
tags: [directness]
```

Fields:

- `category`: `engagement`, `factual_accuracy`, `calibration`, `anti_sycophancy`, or `guardrails`
- `expect`: `engage` or `refuse`
- `messages`: chat messages sent to the target model
- `reference`: optional expected answer content
- `rubric`: judge instructions

## Platform shape

```text
User / evaluator
      ↓
TruthSeek web app + CLI
      ↓
Target model gateway → Judge model / heuristic judge
      ↓
Scorecard: engagement, refusal, calibration, anti-sycophancy, directness
      ↓
CI gate, release gate, model/prompt comparison, enterprise audit artifact
```

## Next product steps

- Add model-vs-model comparison runs
- Add prompt-version tracking
- Add dataset versioning and signed scorecards
- Add human review queue for disputed judge calls
- Add org dashboards and trend lines
- Add red-team case marketplace
- Add exports for SOC2 / AI governance evidence
