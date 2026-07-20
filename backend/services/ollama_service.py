import json
import logging
import urllib.error
import urllib.request
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class OllamaService:
    """
    Simple wrapper around the local Ollama REST API.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:8b",
        timeout: int = 120,
        chat_timeout: int = 600,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        # chat_timeout must cover CPU prompt-prefill (KV-cache fill) PLUS
        # token generation.  With think=False and a small num_ctx, prefill is
        # fast; but we keep a generous ceiling for safety on slow hardware.
        self.chat_timeout = chat_timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        endpoint: str,
        payload: Optional[dict] = None,
        method: str = "GET",
    ) -> Dict:
        url = f"{self.base_url}{endpoint}"

        headers = {
            "Content-Type": "application/json"
        }

        data = None

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=data,
            headers=headers,
            method=method,
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _chat_stream(self, payload: dict) -> str:
        """
        POST to /api/chat with stream=True and collect the full assistant
        reply by reading NDJSON lines one at a time.

        Why streaming avoids the timeout:
        urllib's ``timeout`` is a *socket idle* timeout, not a wall-clock
        deadline.  With stream=False, Ollama writes nothing to the socket
        until it finishes generating the entire response.  On CPU that can
        easily exceed 120 s, causing a socket.timeout.  With stream=True,
        Ollama sends one JSON line per token (~milliseconds apart), so the
        socket is never idle long enough to trip the timer.

        Only ``message.content`` is collected; ``message.thinking`` (the
        Qwen3 reasoning trace) is intentionally ignored even when think=True,
        because we always send think=False.
        """
        url = f"{self.base_url}/api/chat"
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        chunks: list = []

        with urllib.request.urlopen(request, timeout=self.chat_timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()

                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping non-JSON stream line: %s", line)
                    continue

                token = obj.get("message", {}).get("content", "")

                if token:
                    chunks.append(token)

                if obj.get("done"):
                    break

        return "".join(chunks).strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_models(self) -> List[str]:
        """
        Returns the names of locally installed Ollama models.
        """

        try:
            response = self._request("/api/tags")

            models = []

            for model in response.get("models", []):
                name = model.get("name")

                if name:
                    models.append(name)

            return models

        except Exception as e:
            logger.error("Unable to fetch Ollama models: %s", e)
            return []

    def check_health(self) -> Dict:
        """
        Returns service health and available models.
        """

        try:
            models = self.list_models()

            return {
                "status": "online",
                "model": self.model,
                "installed_models": models,
            }

        except Exception as e:
            logger.exception(e)

            return {
                "status": "offline",
                "model": None,
                "installed_models": [],
                "error": str(e),
            }

    def chat(
        self,
        system_prompt: str,
        context: str,
        user_question: str,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Sends a chat request to Ollama.
        """

        if conversation_history is None:
            conversation_history = []

        # Merge the system prompt and context into a single system message.
        # Sending two consecutive system messages can confuse some Ollama
        # builds; one message is cleaner and avoids any ambiguity.
        if context.strip():
            combined_system = (
                f"{system_prompt}\n\n"
                f"Context:\n\n{context}"
            )
        else:
            combined_system = system_prompt

        messages = [
            {
                "role": "system",
                "content": combined_system,
            }
        ]

        messages.extend(conversation_history)

        messages.append(
            {
                "role": "user",
                "content": user_question,
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            # stream=True keeps the socket alive during generation so the
            # socket idle-timeout cannot fire mid-response.
            "stream": True,
            # think=False disables Qwen3's chain-of-thought reasoning mode.
            # By default Qwen3 generates a hidden <think>…</think> trace
            # before the visible answer.  On CPU this trace can be several
            # hundred tokens long, adding tens of seconds of pure overhead
            # for tasks that do not benefit from it (e.g. factual retrieval).
            # Setting think=False tells Ollama to skip that phase entirely.
            # This is a top-level field, not an entry inside "options".
            "think": False,
            "options": {
                # Cap output length.  512 tokens is sufficient for a
                # concise compliance summary.
                "num_predict": 512,
                # Match the KV-cache window to our actual input size.
                # Context (~180 tokens) + system prompt (~80) + question
                # (~30) + response (512) = ~800 tokens.  512 is the minimum
                # Ollama accepts; 1024 gives headroom without waste.
                # Smaller num_ctx = less memory allocated = faster prefill.
                "num_ctx": 1024,
                # Low temperature keeps answers factual and grounded in the
                # supplied context.  Default is 0.8 (creative); 0.1 is
                # near-deterministic, reducing hallucination risk.
                "temperature": 0.1,
                # Restrict token sampling to the top 80% probability mass.
                # Combined with low temperature this further prevents the
                # model from diverging from the context.
                "top_p": 0.8,
                # Mild repetition penalty prevents the model from restating
                # the same finding multiple times, reducing wasted tokens.
                "repeat_penalty": 1.1,
            },
        }

        try:
            return self._chat_stream(payload)

        except urllib.error.HTTPError as e:
            error_body = ""

            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            logger.error("HTTP %s : %s", e.code, error_body)

            return f"HTTP {e.code}: {error_body}"

        except urllib.error.URLError as e:
            logger.error(e)

            return f"Unable to connect to Ollama: {e.reason}"

        except Exception as e:
            logger.exception(e)

            return f"Unexpected error: {e}"