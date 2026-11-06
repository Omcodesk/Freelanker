"""Public pipeline errors; raw provider messages must not reach callers."""


class ContractGenerationError(Exception):
    """Base generation error. Invalid inputs use Pydantic ValidationError."""


class InvalidProviderOutput(ContractGenerationError):
    pass


class ProviderError(ContractGenerationError):
    pass


class GenerationTimeout(ContractGenerationError):
    pass


class ConfigurationError(ContractGenerationError):
    pass
