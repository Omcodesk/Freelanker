"""Optional Groq SDK adapter; client lives only for a single request."""

from ..config import GroqSettings
from ..errors import InvalidProviderOutput, ProviderError


class GroqProvider:
    def __init__(self, settings: GroqSettings):
        self.settings = settings

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        from groq import APITimeoutError, AsyncGroq

        try:
            async with AsyncGroq(api_key=self.settings.api_key.get_secret_value(),
                                 timeout=self.settings.timeout_seconds, max_retries=0) as client:
                response = await client.chat.completions.create(
                    model=self.settings.model,
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_prompt}],
                    response_format={"type": "json_object"}, temperature=0,
                )
        except APITimeoutError:
            raise TimeoutError("Groq request timed out") from None
        except Exception:
            raise ProviderError("Groq request failed") from None
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise InvalidProviderOutput("Groq returned no complete draft")
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise InvalidProviderOutput("Groq returned empty draft content")
        return content
