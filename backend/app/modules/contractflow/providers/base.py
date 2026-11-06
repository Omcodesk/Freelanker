from typing import Protocol


class ContractProvider(Protocol):
    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return a JSON string, without markdown fences."""
        ...
