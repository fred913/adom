"""Tiktoken-based token estimator."""

from typing import Any

from adomcore.services.token_estimator import TokenEstimateRequest, TokenEstimateResult


class TiktokenEstimator:
    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding_name = encoding_name
        self._enc_cache: dict[str, object] = {}

    def _get_enc(self, encoding_name: str) -> object:
        enc = self._enc_cache.get(encoding_name)
        if enc is None:
            import tiktoken

            enc = tiktoken.get_encoding(encoding_name)
            self._enc_cache[encoding_name] = enc
        return enc

    def _resolve_encoding_name(self, config: dict[str, Any] | None) -> str:
        if not config:
            return self._encoding_name
        encoding_name = config.get("encoding_name")
        if isinstance(encoding_name, str) and encoding_name:
            return encoding_name
        return self._encoding_name

    async def estimate(self, request: TokenEstimateRequest) -> TokenEstimateResult:
        import tiktoken

        enc = self._get_enc(self._resolve_encoding_name(request.config))
        assert isinstance(enc, tiktoken.Encoding)
        return TokenEstimateResult(
            token_count=len(enc.encode(request.text)),
            provider="tiktoken",
        )
