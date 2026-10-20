# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/claude_service.py
"""
Claude API service client.

All Claude/AI calls go through this service, scoped by role_context.
The role_context ensures agent output is genuinely personalized per role.
"""
import os
import logging
import json
from typing import AsyncGenerator, Dict, Any, Literal
import anthropic

logger = logging.getLogger(__name__)



class ClaudeService:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")

    def _system_prompt(self, role_context: str) -> str:
        if not role_context:
            return ""
        return f"""You are an AI agent specialized in the {role_context} department of ENY Consulting.
You have deep knowledge of {role_context} processes, terminology, and best practices.
Always respond in a professional, helpful manner appropriate for a {role_context} professional.
When providing advice or analysis, frame it within the context of {role_context} responsibilities and goals."""

    async def invoke(
        self,
        prompt: str,
        role_context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """
        Invoke Claude with optional role context for personalized responses.

        Args:
            prompt: The main prompt/query for Claude
            role_context: Department-specific context (e.g., "sales", "marketing", "ceo")
                         Used to personalize the response based on the caller's role
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)

        Returns:
            Claude's response as a string
        """
        # Build the system prompt with role context if provided
        system_prompt = self._system_prompt(role_context)

        try:
            # Use the Anthropic client to send a message
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract the text content from the response
            if message.content:
                return message.content[0].text if hasattr(message.content[0], 'text') else str(message.content[0])
            else:
                logger.warning("Claude returned empty content")
                return "I apologize, but I couldn't generate a response at this time."

        except Exception as e:
            logger.error(f"Error invoking Claude: {e}")
            # Return a helpful error message rather than crashing
            return f"I encountered an error while processing your request: {str(e)}"

    async def stream_invoke(
        self,
        prompt: str,
        role_context: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Yield Claude text deltas as they arrive from Anthropic."""
        try:
            async with self.async_client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=self._system_prompt(role_context),
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            logger.error(f"Error streaming Claude response: {exc}")
            raise

    async def invoke_with_image(
        self,
        prompt: str,
        image_base64: str,
        media_type: Literal["image/jpeg", "image/png", "image/webp"],
        role_context: str = "",
        max_tokens: int = 1800,
        temperature: float = 0.2,
    ) -> str:
        """Assess a user-submitted creative image without storing or publishing it."""
        message = await self.async_client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=self._system_prompt(role_context),
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        text = next(
            (block.text for block in message.content if getattr(block, "type", None) == "text"),
            None,
        )
        if not text:
            raise ValueError("Claude returned an empty creative assessment")
        return text

    async def score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score a lead from supplied evidence; callers must handle model/API failures."""
        prompt = f"""Evaluate this prospective lead using only the supplied data. Do not infer missing facts.
Use component scores from 0 to 100:
- intent_score (40%): explicit interest, inquiry, or purchase-intent evidence
- fit_score (30%): explicit evidence of fit with ENY's business-analysis, AI-strategy, training, or consulting offers
- engagement_score (30%): explicit recent engagement evidence such as attendance, clicks, replies, or visits
If a component has no evidence, score that component 0 and say it is unknown; do not reward contact completeness.
Calculate the final score as round(intent_score * 0.4 + fit_score * 0.3 + engagement_score * 0.3).
The server will derive the category: hot >= 85, warm >= 70, follow-up >= 50, otherwise cold.
Return only JSON with integer component scores, a concise evidence-based reasoning string,
an evidence array, an unknowns array, and a human next_best_action. Do not return a category.

Lead data:
{json.dumps(lead_data, ensure_ascii=True, default=str)}
"""
        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=700,
            temperature=0,
            system=self._system_prompt("sales and enrollment"),
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            None,
        )
        if not text:
            raise ValueError("Claude returned an empty lead-scoring response")
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Claude returned invalid JSON for lead scoring") from exc
        if not isinstance(result, dict):
            raise ValueError("Claude lead-scoring response must be a JSON object")

        component_names = ("intent_score", "fit_score", "engagement_score")
        components: dict[str, int] = {}
        for name in component_names:
            value = result.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
                raise ValueError(f"Claude returned an invalid {name}")
            components[name] = round(value)
        reasoning = result.get("reasoning")
        action = result.get("next_best_action")
        evidence = result.get("evidence")
        unknowns = result.get("unknowns")
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise ValueError("Claude omitted the scoring reasoning")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("Claude omitted the recommended next action")
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise ValueError("Claude returned invalid scoring evidence")
        if not isinstance(unknowns, list) or not all(isinstance(item, str) for item in unknowns):
            raise ValueError("Claude returned invalid scoring unknowns")

        score = round(
            components["intent_score"] * 0.4
            + components["fit_score"] * 0.3
            + components["engagement_score"] * 0.3
        )
        return {
            "score": score,
            "category": "hot" if score >= 85 else "warm" if score >= 70 else "follow-up" if score >= 50 else "cold",
            "reasoning": reasoning.strip(),
            "evidence": evidence,
            "unknowns": unknowns,
            "score_factors": components,
            "next_best_action": action.strip(),
            "score_origin": "claude",
        }

    async def generate_content(
        self,
        content_type: str,
        topic: str,
        brand_voice: str = "ENY Consulting",
        length: str = "medium",
    ) -> str:
        """
        Generate content for marketing agents.
        """
        length_guide = {
            "short": "1-2 paragraphs",
            "medium": "3-5 paragraphs",
            "long": "8-12 paragraphs"
        }.get(length, "3-5 paragraphs")

        prompt = f"""
        Generate a {content_type} about "{topic}" in the {brand_voice} brand voice.
        The content should be approximately {length_guide} long.
        Make it engaging, professional, and aligned with ENY Consulting's expertise in business analysis, AI strategy, and consulting.

        Topic: {topic}
        Content Type: {content_type}
        Brand Voice: {brand_voice}
        Target Length: {length_guide}
        """

        return await self.invoke(
            prompt=prompt,
            role_context="marketing",
            max_tokens=1500,
            temperature=0.8  # Higher temperature for more creative content
        )

    async def analyze_pipeline(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze pipeline data for insights and recommendations.
        """
        prompt = f"""
        Analyze the following sales pipeline data and provide insights and recommendations.
        Look for trends, bottlenecks, opportunities, and risks.

        Pipeline Data:
        {pipeline_data}

        Return your analysis in JSON format:
        {{
            "insights": [<list of key insights>],
            "risks": [<list of potential risks>],
            "opportunities": [<list of identified opportunities>],
            "recommended_actions": [<list of specific recommended actions>],
            "forecast_summary": "<brief summary of forecast and confidence>"
        }}
        """

        try:
            response = await self.invoke(
                prompt=prompt,
                role_context="ceo",  # Pipeline analysis is typically for leadership
                max_tokens=1000,
                temperature=0.5
            )

            # Try to parse JSON response
            import json
            try:
                result = json.loads(response)
                # Ensure all expected fields are present
                for field in ["insights", "risks", "opportunities", "recommended_actions", "forecast_summary"]:
                    if field not in result:
                        result[field] = [] if field != "forecast_summary" else "Analysis unavailable"
                return result
            except json.JSONDecodeError:
                logger.warning(f"Claude did not return valid JSON for pipeline analysis: {response}")
                return {
                    "insights": ["Unable to parse analysis response"],
                    "risks": [],
                    "opportunities": [],
                    "recommended_actions": ["Review pipeline data manually"],
                    "forecast_summary": "Analysis unavailable due to parsing error"
                }

        except Exception as e:
            logger.error(f"Error in pipeline analysis: {e}")
            return {
                "insights": [f"Error occurred: {str(e)}"],
                "risks": [],
                "opportunities": [],
                "recommended_actions": ["Review pipeline data manually"],
                "forecast_summary": "Analysis unavailable due to error"
            }