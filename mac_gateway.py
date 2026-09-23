"""Local authenticated OpenAI API bridge to Docker Model Runner on macOS."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_KEY = os.environ["VLLM_API_KEY"]
MODEL_URL = os.environ["MODEL_URL"].rstrip("/")
MODEL_ID = os.environ["MODEL_ID"]
if not API_KEY:
    raise ValueError("VLLM_API_KEY must not be empty")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Do not log prompts or authorization headers.

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        actual = self.headers.get("Authorization", "").encode()
        expected = ("Bearer " + API_KEY).encode()
        if hmac.compare_digest(actual, expected):
            return True
        self.reply(401, {"error": {"message": "Invalid API key"}})
        return False

    def do_GET(self):
        if self.path == "/health":
            try:
                with urlopen(MODEL_URL + "/models", timeout=4) as response:
                    models = json.load(response).get("data", [])
                if not any(model["id"].removeprefix("docker.io/") == MODEL_ID.removeprefix("docker.io/") for model in models):
                    raise ValueError("Model not registered")
            except (URLError, TimeoutError, ValueError, KeyError):
                self.reply(503, {"status": "unavailable"})
                return
            # Checks runner connectivity and registration, not model warmup.
            self.reply(200, {"status": "ok"})
        elif self.path == "/v1/models":
            if self.authorized():
                self.reply(200, {"object": "list", "data": [
                    {"id": "qwen", "object": "model", "owned_by": "local"}
                ]})
        else:
            self.reply(404, {"error": {"message": "Use /v1/chat/completions with model qwen"}})

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/v1/chat/completions":
            self.reply(404, {"error": {"message": "Unknown endpoint"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4 * 1024 * 1024:
                raise ValueError("Request must be between 1 byte and 4 MiB")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or payload.get("model") != "qwen":
                raise ValueError("Use model qwen")
            payload["model"] = MODEL_ID
            payload.setdefault("chat_template_kwargs", {"enable_thinking": False})
        except (ValueError, UnicodeDecodeError) as error:
            self.reply(400, {"error": {"message": str(error)}})
            return
        request = Request(MODEL_URL + "/chat/completions",
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=300)
        except HTTPError as error:
            self.reply(error.code, {"error": {"message": error.read().decode(errors="replace")}})
            return
        except (URLError, TimeoutError):
            self.reply(502, {"error": {"message": "Docker Model Runner is unavailable"}})
            return
        with response:
            if payload.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                try:
                    for line in response:
                        if line.startswith(b"data: ") and line.strip() != b"data: [DONE]":
                            event = json.loads(line[6:])
                            event["model"] = "qwen"
                            line = b"data: " + json.dumps(event).encode() + b"\n"
                        self.wfile.write(line)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    return
            else:
                result = json.load(response)
                result["model"] = "qwen"
                self.reply(200, result)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
