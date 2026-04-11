"""Anthropic count_tokens estimator."""

import os

from adomcore.services.token_estimator import TokenEstimateRequest, TokenEstimateResult


class AnthropicCountTokensEstimator:
    async def estimate(self, request: TokenEstimateRequest) -> TokenEstimateResult:
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        response = await client.messages.count_tokens(
            model=request.model_id,
            messages=[{"role": "user", "content": request.text}],
        )
        return TokenEstimateResult(
            token_count=response.input_tokens,
            provider="anthropic_count_tokens",
        )
