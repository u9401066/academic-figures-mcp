"""Domain exceptions — raised by domain and application layers."""


class DomainError(Exception):
    """Base exception for all domain errors."""


class PaperNotFoundError(DomainError):
    """Paper could not be retrieved from the catalog."""


class GenerationError(DomainError):
    """Image generation or editing failed."""


class ConfigurationError(DomainError):
    """Required configuration is missing or invalid."""


class ImageNotFoundError(DomainError):
    """Referenced image file does not exist on disk."""


class ValidationError(DomainError):
    """User or tool input failed validation."""


class ProviderCapabilityError(DomainError):
    """Selected provider cannot perform the requested operation."""
