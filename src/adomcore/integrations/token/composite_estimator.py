"""Composite token estimator — routes by ModelSpec.token_estimate_provider."""

from adomcore.domain.models import TokenEstimateProviderKind
from adomcore.integrations.token.anthropic_count_tokens_estimator import (
    AnthropicCountTokensEstimator,
)
from adomcore.integrations.token.heuristic_estimator import HeuristicTokenEstimator
from adomcore.integrations.token.tiktoken_estimator import TiktokenEstimator
from adomcore.services.token_estimator import TokenEstimateRequest, TokenEstimateResult


class CompositeTokenEstimator:
    def __init__(self) -> None:
        self._heuristic = HeuristicTokenEstimator()
        self._tiktoken = TiktokenEstimator()
        self._anthropic = AnthropicCountTokensEstimator()

    async def estimate(
        self,
        request: TokenEstimateRequest,
        provider: TokenEstimateProviderKind = TokenEstimateProviderKind.HEURISTIC,
    ) -> TokenEstimateResult:
        if provider == TokenEstimateProviderKind.TIKTOKEN:
            return await self._tiktoken.estimate(request)
        if provider == TokenEstimateProviderKind.ANTHROPIC_COUNT_TOKENS:
            return await self._anthropic.estimate(request)
        return await self._heuristic.estimate(request)
