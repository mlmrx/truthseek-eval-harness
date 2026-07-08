# Changelog

## 0.7.0

- `Configure target model…`: detect local servers (Ollama, LM Studio, vLLM, llama.cpp),
  list loaded models, and write the `target` block into `config.yaml` (preserving any existing
  `system_prompt`, `judge`, and `thresholds`).
- Run the eval, mock eval, and strict gate; compare models; open the HTML scorecard in a webview.
- `truthseek.pythonPath` setting to select the Python interpreter.
