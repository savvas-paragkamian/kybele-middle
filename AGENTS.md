# Repository guidance

## Purpose and scope

`kybele-middle` manages local LLM inference for the chat interface in
[KYBELE-UI, develop branch](https://github.com/steninidak/KYBELE-UI/tree/develop).
Keep this repository focused on model serving and configuration. The frontend
and Open WebUI belong to the UI project. Retrieval/SIBiLS orchestration is not
implemented here; do not describe it as available.

Keep changes minimal and document runnable terminal commands in `README.md`.
Preserve unrelated work, including staged changes. Do not edit the other
repository unless the task explicitly includes it.

## Two separate runtime paths

| Path | Files | Intended environment |
| --- | --- | --- |
| NVIDIA deployment | `Dockerfile`, `compose.yaml`, `serve.sh` | Linux, NVIDIA GPU with 16 GB VRAM, 32 GB system RAM; vLLM |
| Mac smoke test | `Dockerfile.mac`, `compose.mac.yaml`, `start_mac.py` | Apple Silicon; API gateway in Docker, Metal inference in Docker Model Runner |

- Both images use Ubuntu 24.04 LTS. Keep runtime versions pinned and verify
  upstream compatibility before changing them.
- NVIDIA presets are `qwen`, `gemma`, and `mistral`. Run one model at a time;
  do not assume all three fit in 16 GB VRAM simultaneously.
- Preserve conservative context and concurrency defaults unless measured results
  justify a change. System RAM does not automatically extend VRAM.
- The Mac path uses Qwen3 0.6B GGUF via Docker Model Runner on the host, with
  Metal GPU offload. The Linux gateway container itself has no GPU access.
  `MODEL_PRESET` does not select the Mac model. Do not imply that Mac testing
  validates NVIDIA performance or memory use. Docker Desktop manages the Mac
  inference backend version. Keep the 8,192-token context unless a task requires
  changing it.
- `compose.mac.yaml` is standalone. Use `-f compose.mac.yaml`; do not merge it
  with `compose.yaml`. Both publish port 8000 by default.

## API and configuration

- Preserve the OpenAI-compatible `/v1/models` and `/v1/chat/completions` interface,
  including streaming, for the frontend/Open WebUI integration.
- NVIDIA model aliases match their presets; the Mac model alias is `qwen`.
- `.env.example` documents settings. Keep `.env`, Hugging Face tokens, and API
  keys out of version control, image layers, and diagnostic output.
- `mac_gateway.py` enforces `VLLM_API_KEY` and maps the public `qwen` alias to
  the configured `MODEL_ID` and `MODEL_URL`. Preserve authenticated access,
  error handling, and streaming. Docker Model Runner itself ignores API keys;
  keep host binding local by default.
- Preserve named model-cache volumes. Do not delete downloaded weights as part
  of routine rebuilds or troubleshooting.
- Gemma requires Hugging Face access and acceptance of its model license.
- Keep `.dockerignore` restrictive; explicitly allow files required by new
  Docker `COPY` instructions.

## Validation

Run these lightweight checks from the repository root after relevant changes:

```sh
sh -n serve.sh
docker compose --env-file .env.example config --quiet
docker compose -f compose.mac.yaml --env-file .env.example config --quiet
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

These checks validate shell syntax, configuration, and gateway behavior with a mock
upstream, not image builds or model inference. Gateway tests bind local loopback
ports. For runtime changes, build and smoke-test the affected path when
Docker and suitable hardware are available:

```sh
# NVIDIA host
docker compose up -d --build
docker compose logs -f vllm

# Apple Silicon Mac (separate alternative)
python3 start_mac.py
docker compose -f compose.mac.yaml logs -f llm
```

Use a configured local API key for runtime checks. Check `/health`, authenticated
`/v1/models`, and a short chat completion; check streaming when changing API
behavior. Follow the examples in `README.md`. Report exactly which checks ran
and any hardware or Docker limitations; never claim inference passed based only
on Compose validation. Do not add an elaborate test framework for documentation
or simple container configuration changes.

## Troubleshooting

Read the full failing command output before diagnosing a build failure. For Mac
build logs, use:

```sh
docker compose -f compose.mac.yaml --progress plain build
```

Distinguish missing release tags, network/TLS failures, compilation errors,
model access failures, and memory exhaustion. Do not change version pins or
disable TLS verification based only on a truncated error line. Verify model
identifiers, release tags, and flags against upstream sources when changing them.
