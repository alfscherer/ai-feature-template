from app.llm.providers.base import LLMProvider


class ProviderRegistry:
    """Looks up a configured provider instance by name.

    Kept deliberately dumb: it doesn't know how to construct providers (that's application
    wiring, done once at startup) and it doesn't pick a default (that's configuration).
    """

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        try:
            return self._providers[name]
        except KeyError:
            raise ValueError(f"Unknown provider: {name!r}") from None

    def names(self) -> list[str]:
        return list(self._providers)
