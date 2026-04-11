"""Heuristic token estimator — len(text) // 4 fallback."""

from adomcore.services.token_estimator import TokenEstimateRequest, TokenEstimateResult


class HeuristicTokenEstimator:
    async def estimate(self, request: TokenEstimateRequest) -> TokenEstimateResult:
        return TokenEstimateResult(
            token_count=len(request.text) // 4,
            provider="heuristic",
        )
