# kybele-middle

Local LLM serving for [KYBELE-UI](https://github.com/steninidak/KYBELE-UI/tree/develop).
This repository runs vLLM; the chat interface / Open WebUI lives in the UI project.

```text
KYBELE-UI / Open WebUI → vLLM OpenAI-compatible API → local GPU model
```

## Test on your Mac (Apple Silicon)

`Dockerfile.mac` and the standalone `compose.mac.yaml` run **llama.cpp on CPU**
inside Ubuntu 24.04, with a small [Qwen3 0.6B Q8 model](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF).
This tests the chat API locally; it does not test vLLM or NVIDIA performance.
The container does not use Apple's Metal GPU. The NVIDIA setup below is unchanged.

Start Docker Desktop first. Give its Linux VM at least 4 GB RAM and 4 CPU cores
for this small model and the build. Then, from this directory:

```sh
# Only copy if you have not already created .env:
cp -n .env.example .env
# Edit .env and set VLLM_API_KEY to your own secret.
docker compose -f compose.mac.yaml up -d --build
docker compose -f compose.mac.yaml logs -f llm
```

The first build compiles llama.cpp (pinned to `b10524`); first startup downloads
the model. Both need internet access and may take several minutes. Subsequent
starts reuse the image and model cache. Wait for a healthy service:

```sh
docker compose -f compose.mac.yaml ps
curl --fail http://localhost:8000/health
```

Test a chat request (replace `YOUR_SECRET` with the key from `.env`):

```sh
curl http://localhost:8000/v1/chat/completions \
  -H 'Authorization: Bearer YOUR_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen","messages":[{"role":"user","content":"Say hello in Greek."}],"max_tokens":128}'
```

For Open WebUI running on the host, use `http://localhost:8000/v1`, your API key,
and model `qwen`. For Open WebUI in Docker, attach its container to
`kybele-middle-mac_default` and use `http://llm:8000/v1`.
The Mac model allows 8,192 tokens total for the prompt, chat history, and generated
response. Longer conversations must be shortened or started fresh when they reach
that limit.

This Mac configuration always loads the small Qwen model; `MODEL_PRESET` in
`.env` applies only to the NVIDIA setup. Both setups use port 8000 by default,
so stop one before starting the other (or change `PORT`).

```sh
docker compose -f compose.mac.yaml down
```

The model cache persists after stopping. See the upstream
[llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
for API details.

## NVIDIA deployment requirements

- Linux machine with an NVIDIA GPU supporting BF16 (Ampere or newer), 16 GB VRAM and 32 GB RAM.
- Docker Engine, Docker Compose v2+, NVIDIA Container Toolkit, and a driver compatible with the CUDA runtime installed by vLLM. Verify GPU access with `nvidia-smi` on the host.
- Internet access for the initial image build and model downloads, plus disk space for the image and cached weights (allow at least 40 GB).

The image uses Ubuntu **24.04 LTS**, a supported stable release with Python 3.12,
and pins vLLM to **0.17.0**. Ubuntu 26.04 is newer; 24.04 is selected for the
Python compatibility of this vLLM baseline. CUDA user-space dependencies come
from the vLLM/PyTorch wheels; the NVIDIA driver belongs on the host.
This NVIDIA configuration cannot run GPU inference in Docker Desktop on macOS.

## Models

| Preset | Hugging Face model | Precision |
| --- | --- | --- |
| `qwen` (default) | [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | BF16 |
| `gemma` | [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | BF16 |
| `mistral` | [mistralai/Ministral-3-3B-Instruct-2512-BF16](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-BF16) | BF16 |

Only **one model runs at a time**. These small models are starting choices for
16 GB VRAM, not a measured memory guarantee. Defaults cap the combined input and
output context at 4,096 tokens, concurrency at two sequences, and GPU allocation
at 85%. Eager execution avoids CUDA graph memory overhead. Gemma and Ministral
are configured for text chat only. Actual capacity needs validation on your GPU;
reduce context/concurrency if startup runs out of memory. System RAM does not
automatically extend VRAM.

## Run

```sh
cp .env.example .env
# Edit .env: set a random VLLM_API_KEY and choose MODEL_PRESET.
docker compose up -d --build
docker compose logs -f vllm
```

For Gemma, first accept the model license on Hugging Face and set `HF_TOKEN` to
a token with access. Tokens stay in the ignored `.env`, outside the image.
First startup downloads model weights into the persistent `model-cache` volume.
Startup may take several minutes; health checks do not imply downloads are done.

Switch models by changing `MODEL_PRESET` in `.env` to `qwen`, `gemma`, or `mistral`,
then running `docker compose up -d`. Compose recreates the single service, releasing
the previous model's GPU memory. Chat is unavailable while the next model loads.
Stop with `docker compose down`; cached weights remain.

## Connect Open WebUI / KYBELE-UI

In Open WebUI's admin connection settings, add an OpenAI-compatible connection:

- Base URL: `http://localhost:8000/v1` when its backend runs directly on this host.
- API key: the value of `VLLM_API_KEY` from `.env`.
- Model: `qwen`, `gemma`, or `mistral`, matching the active preset. `/v1/models`
  reports only the currently loaded model; refresh the model list after switching.

For Open WebUI in another container, `localhost` refers to that container.
Attach it to this Compose project's default network (`kybele-middle_default`
unless the project name is overridden) and use `http://vllm:8000/v1`.
For a remote frontend backend, set `BIND_ADDRESS` to a reachable host interface
and use that host's address. Keep the API key in the frontend's backend;
do not embed it in public browser JavaScript.

The API supports `/v1/chat/completions`, including `stream: true`. For example:

```sh
export VLLM_API_KEY='your-key-from-.env'
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen","messages":[{"role":"user","content":"Hello!"}],"max_tokens":128}'
```

This provides the inference endpoint; wiring the UI repository to it and any
retrieval/SIBiLS orchestration are separate integration work.

References: [vLLM installation](https://docs.vllm.ai/en/v0.17.0/getting_started/installation/gpu/),
[Open WebUI integration](https://docs.vllm.ai/en/v0.17.0/deployment/frameworks/open-webui/).
