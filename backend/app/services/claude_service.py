# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/claude_service.py
"""
Claude API service client.

All Claude/AI calls go through this service, scoped by role_context.
The role_context ensures agent output is genuinely personalized per role.
"""
import os
import logging
from typing import Optional, Dict, Any
import anthropic

logger = logging.getLogger(__name__)


class ClaudeService:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")

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
        system_prompt = ""
        if role_context:
            system_prompt = f"""You are an AI agent specialized in the {role_context} department of ENY Consulting.
You have deep knowledge of {role_context} processes, terminology, and best practices.
Always respond in a professional, helpful manner appropriate for a {role_context} professional.
When providing advice or analysis, frame it within the context of {role_context} responsibilities and goals."""

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

    async def score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized method for lead scoring (used by ENY-SALES-SCORE agent).
        """
        prompt = f"""
        Score the following lead on a scale of 1-100 based on engagement, demographics, and intent signals.
        Consider factors like:
        - Lead source and quality
        - Engagement history (emails opened, clicks, website visits)
        - Demographic fit with ideal customer profile
        - Expressed interest and timing
        - Budget and authority indicators

        Lead Data:
        {lead_data}

        Return your response in JSON format:
        {{
            "score": <number between 1-100>,
            "reasoning": "<brief explanation of the score>",
            "recommended_tags": [<list of suggested tags for this lead>],
            "next_best_action": "<suggested immediate action>"
        }}
        """

        try:
            response = await self.invoke(
                prompt=prompt,
                role_context="sales",
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent scoring
            )

            # Try to parse JSON response
            import json
            try:
                result = json.loads(response)
                # Validate required fields
                if "score" not in result:
                    result["score"] = 50  # Default middle score
                if "reasoning" not in result:
                    result["reasoning"] = "Score calculated based on lead data"
                if "recommended_tags" not in result:
                    result["recommended_tags"] = []
                if "next_best_action" not in result:
                    result["next_best_action"] = "Review lead manually"
                return result
            except json.JSONDecodeError:
                logger.warning(f"Claude did not return valid JSON for lead scoring: {response}")
                # Fallback response
                return {
                    "score": 50,
                    "reasoning": "Unable to parse scoring response",
                    "recommended_tags": [],
                    "next_best_action": "Review lead manually"
                }

        except Exception as e:
            logger.error(f"Error in lead scoring: {e}")
            return {
                "score": 0,
                "reasoning": f"Error occurred: {str(e)}",
                "recommended_tags": ["error"],
                "next_best_action": "Review lead manually"
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