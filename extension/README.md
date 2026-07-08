# TruthSeek Eval Harness — VS Code extension

A thin front end for the [TruthSeek Eval Harness](https://github.com/mlmrx/truthseek-eval-harness)
Python project. Open the harness folder as your workspace, then drive it from the Command Palette.

## Commands

All commands are under the **TruthSeek** category:

| Command | What it does |
| --- | --- |
| **Configure target model…** | Pick a local server (Ollama, LM Studio, vLLM, llama.cpp), auto-discovers the models loaded there, and writes the `target` block into `config.yaml`. |
| **Run eval (config.yaml)** | Runs `python -m harness.cli run --config config.yaml --cases cases/` in a terminal. |
| **Run mock eval (offline)** | Runs the offline mock suite — no model, no network. |
| **Run strict gate** | Runs with `--strict`, the same gate CI uses. |
| **Compare models…** | Runs the same cases against several models head-to-head. |
| **Open scorecard** | Opens the generated `out/scorecard.html` in a webview. |

Model discovery mirrors the harness's own logic: it tries the Ollama `/api/tags` endpoint
first, then falls back to the OpenAI-compatible `/models` listing. Every "run" command shells
out to the harness CLI, so results are identical to running it by hand.

## Settings

- `truthseek.pythonPath` (default `python`) — the Python executable used to run the harness.
  Point it at a virtualenv interpreter if the harness is installed there.

## Requirements

- The workspace is a TruthSeek harness checkout (has `harness/`, `cases/`, `config.example.yaml`).
- Python with the harness dependencies installed (`pip install -r requirements.txt`).

## License

MIT
