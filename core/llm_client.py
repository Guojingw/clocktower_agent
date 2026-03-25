import json
import os
import re
import socket
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


def call_ollama(prompt, model=MODEL_NAME):
    timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTPError: {e.code} {e.reason}. {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama connection error: {e.reason}") from e
    except (TimeoutError, socket.timeout) as e:
        raise RuntimeError(
            f"Ollama request timed out after {timeout_seconds}s. "
            f"Try a smaller prompt or smaller model."
        ) from e

    return json.loads(body)["response"]


def extract_json(text: str):
    text = text.strip()

    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(1))

    print("=== 模型原始输出开始 ===")
    print(text)
    print("=== 模型原始输出结束 ===")
    raise ValueError("模型输出中没有合法 JSON。")