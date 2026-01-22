"""Decoder Custom exceptions."""


class DecoderError(Exception):
    """Base exception for Decoder errors."""


class SymbolNotFoundError(DecoderError):
    """Symbol not found in the index."""


class ParseError(DecoderError):
    """Error parsing a source file."""
