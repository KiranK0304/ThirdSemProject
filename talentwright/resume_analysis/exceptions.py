"""Exceptions for resume text extraction and analysis."""


class ResumeAnalysisError(Exception):
    """Base exception for all resume analysis operations."""


class UnsupportedFileFormatError(ResumeAnalysisError):
    """Raised when an uploaded resume file extension or format is unsupported."""


class TextExtractionError(ResumeAnalysisError):
    """Raised when text extraction from a resume file fails."""


class EmptyResumeError(ResumeAnalysisError):
    """Raised when the extracted text from a resume is empty or unreadable."""


class LLMConfigurationError(ResumeAnalysisError):
    """Raised when the LLM API key or base URL is misconfigured."""


class ResumeParsingError(ResumeAnalysisError):
    """Raised when LLM structuring or parsing fails."""
