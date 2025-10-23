"""
Insights Generation Module

Combines summary generation, quote extraction, and insights formatting.
"""

import json
import logging
import os
from dataclasses import dataclass

try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """Structured summary with overview and key points."""

    overview: str  # 2-3 sentence overview
    key_points: list[str]  # 3-5 bullet points
    themes: list[str]  # Main themes discussed


@dataclass
class Quote:
    """A memorable quote with context and timing."""

    text: str  # The quote itself
    timestamp: float  # Seconds into video
    timestamp_link: str | None  # YouTube link if applicable
    context: str  # Why this quote matters


class SummaryGenerator:
    """Generate concise summaries from transcripts using Claude."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize summary generator.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.
            model: Model to use. If not provided, uses AMPLIFIER_MODEL_DEFAULT or claude-3-haiku-20240307.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not available. Install with: pip install anthropic")

        # Get API key from param or environment
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Please set it in your environment or pass it as a parameter.")

        # Get model from param or environment
        self.model = model or os.getenv("AMPLIFIER_MODEL_DEFAULT", "claude-3-haiku-20240307")

        # Initialize Anthropic client
        self.client = Anthropic(api_key=self.api_key)

    def generate(self, transcript_text: str, title: str) -> Summary:
        """Generate a concise summary from transcript text.

        Args:
            transcript_text: Full transcript text
            title: Title of the video/content

        Returns:
            Summary object with overview, key points, and themes
        """
        prompt = f"""Please summarize this transcript titled "{title}".

Provide:
1. A 2-3 sentence overview that captures the essence of the content
2. 3-5 key takeaways or insights (as bullet points)
3. 2-4 main themes discussed

Focus on actionable insights and important ideas. Be concise.

Transcript:
{transcript_text[:15000]}  # Limit to first 15k chars to avoid token limits

Please respond in this exact format:
OVERVIEW:
[Your 2-3 sentence overview here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
[etc.]

THEMES:
- [Theme 1]
- [Theme 2]
[etc.]
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for more focused summaries
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Parse the response - extract text from the first text block
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content = block.text  # type: ignore[attr-defined]
                    break
            if not content:
                content = str(response.content[0])
            return self._parse_summary(content)

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            # Return a fallback summary
            return Summary(
                overview=f"Summary generation failed for '{title}'.",
                key_points=["Unable to extract key points due to API error"],
                themes=["Error occurred during processing"],
            )

    def _parse_summary(self, response_text: str) -> Summary:
        """Parse Claude's response into a Summary object.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed Summary object
        """
        lines = response_text.strip().split("\n")
        overview = ""
        key_points = []
        themes = []

        section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("OVERVIEW:"):
                section = "overview"
                continue
            if line.startswith("KEY POINTS:"):
                section = "key_points"
                continue
            if line.startswith("THEMES:"):
                section = "themes"
                continue

            if section == "overview":
                if overview:
                    overview += " " + line
                else:
                    overview = line
            elif section == "key_points" and line.startswith("- "):
                key_points.append(line[2:])
            elif section == "themes" and line.startswith("- "):
                themes.append(line[2:])

        # Ensure we have at least some content
        if not overview:
            overview = "Summary could not be generated."
        if not key_points:
            key_points = ["No key points extracted"]
        if not themes:
            themes = ["No themes identified"]

        return Summary(overview=overview, key_points=key_points, themes=themes)


class QuoteExtractor:
    """Extract memorable quotes from transcripts using Claude."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize quote extractor.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.
            model: Model to use. If not provided, uses AMPLIFIER_MODEL_DEFAULT or claude-3-haiku-20240307.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not available. Install with: pip install anthropic")

        # Get API key from param or environment
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Please set it in your environment or pass it as a parameter.")

        # Get model from param or environment
        self.model = model or os.getenv("AMPLIFIER_MODEL_DEFAULT", "claude-3-haiku-20240307")

        # Initialize Anthropic client
        self.client = Anthropic(api_key=self.api_key)

    def extract(self, transcript, video_url: str | None, video_id: str) -> list[Quote]:
        """Extract memorable quotes from a transcript.

        Args:
            transcript: Transcript object with segments
            video_url: Optional YouTube URL for generating timestamp links
            video_id: Video ID for reference

        Returns:
            List of Quote objects with timestamps and context
        """
        # Prepare transcript text with timestamps for better extraction
        transcript_with_timestamps = self._format_transcript_with_timestamps(transcript)

        prompt = f"""Extract 3-5 memorable, insightful quotes from this transcript.

Choose quotes that:
- Capture key ideas or surprising insights
- Are complete thoughts (not fragments)
- Would stand alone as meaningful statements
- Represent different aspects of the content

For each quote, provide:
1. The exact quote text
2. The timestamp (in seconds) when it appears
3. Context explaining why this quote is significant

Transcript:
{transcript_with_timestamps[:15000]}  # Limit to first 15k chars

Please respond in JSON format with an array of quotes:
[
  {{
    "text": "The exact quote here",
    "timestamp": 123.5,
    "context": "Why this quote matters"
  }}
]
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for accurate extraction
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Parse the response - extract text from the first text block
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content = block.text  # type: ignore[attr-defined]
                    break
            if not content:
                content = str(response.content[0])
            quotes_data = self._parse_quotes_response(content)

            # Convert to Quote objects with YouTube links if applicable
            quotes = []
            for quote_data in quotes_data:
                timestamp_link = None
                if video_url and "youtube.com" in video_url:
                    seconds = int(quote_data.get("timestamp", 0))
                    timestamp_link = f"https://youtube.com/watch?v={video_id}&t={seconds}s"

                quotes.append(
                    Quote(
                        text=quote_data.get("text", ""),
                        timestamp=quote_data.get("timestamp", 0.0),
                        timestamp_link=timestamp_link,
                        context=quote_data.get("context", ""),
                    )
                )

            return quotes

        except Exception as e:
            logger.error(f"Failed to extract quotes: {e}")
            # Return empty list on failure
            return []

    def _format_transcript_with_timestamps(self, transcript) -> str:
        """Format transcript with timestamps for better quote extraction.

        Args:
            transcript: Transcript object with segments

        Returns:
            Formatted transcript text with timestamps
        """
        if not transcript.segments:
            # If no segments, return plain text
            return transcript.text

        # Format with timestamps every few segments
        formatted = []
        for i, segment in enumerate(transcript.segments[:100]):  # Limit segments to avoid token limits
            if i % 5 == 0:  # Add timestamp every 5 segments
                minutes = int(segment.start // 60)
                seconds = int(segment.start % 60)
                formatted.append(f"\n[{minutes:02d}:{seconds:02d}] ")
            formatted.append(segment.text + " ")

        return "".join(formatted)

    def _parse_quotes_response(self, response_text: str) -> list[dict]:
        """Parse Claude's response to extract quote data.

        Args:
            response_text: Raw response from Claude

        Returns:
            List of quote dictionaries
        """
        try:
            # Try to find JSON in the response
            response_text = response_text.strip()

            # If the response starts with ```json, extract the JSON
            if response_text.startswith("```json"):
                response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

            # Parse the JSON
            quotes_data = json.loads(response_text.strip())

            # Ensure it's a list
            if not isinstance(quotes_data, list):
                logger.warning("Quote response was not a list")
                return []

            return quotes_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quotes JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error parsing quotes response: {e}")
            return []


def generate_insights(
    summary: Summary | None,
    quotes: list[Quote] | None,
    title: str,
) -> str:
    """
    Combine summary and quotes into a single insights document.

    Creates a unified document with overview, key points, notable quotes,
    and central themes. Handles cases where summary or quotes may be missing.

    Args:
        summary: Summary object with overview and key points
        quotes: List of Quote objects with timestamps
        title: Title of the video/content

    Returns:
        Formatted markdown insights document
    """
    lines = [
        f"# Insights: {title}",
        "",
    ]

    # Add overview if available
    if summary and summary.overview:
        lines.extend(
            [
                "## Overview",
                "",
                summary.overview,
                "",
            ]
        )

    # Add key points if available
    if summary and summary.key_points:
        lines.extend(
            [
                "## Key Points",
                "",
            ]
        )

        # Integrate quotes with key points where relevant
        for point in summary.key_points:
            lines.append(f"- {point}")

        lines.append("")

    # Add notable quotes section if quotes are available
    if quotes:
        lines.extend(
            [
                "## Notable Quotes",
                "",
            ]
        )

        # Select most impactful quotes (limit to top 5-7)
        notable_quotes = quotes[:7] if len(quotes) > 7 else quotes

        for quote in notable_quotes:
            # Format quote with timestamp
            timestamp_str = _format_timestamp(quote.timestamp)

            # Add quote text
            lines.append(f'> "{quote.text}"')

            # Add timestamp and link if available
            if quote.timestamp_link:
                lines.append(f"> — [{timestamp_str}]({quote.timestamp_link})")
            else:
                lines.append(f"> — [{timestamp_str}]")

            # Add context if particularly insightful
            if quote.context:
                lines.append(">")
                lines.append(f"> *{quote.context}*")

            lines.append("")

    # Add central themes if available
    if summary and summary.themes:
        lines.extend(
            [
                "## Central Themes",
                "",
            ]
        )

        for theme in summary.themes:
            lines.append(f"- {theme}")

        lines.append("")

    # Add additional quotes section if there are many quotes
    if quotes and len(quotes) > 7:
        lines.extend(
            [
                "## Additional Quotes",
                "",
            ]
        )

        for quote in quotes[7:]:
            timestamp_str = _format_timestamp(quote.timestamp)

            # More compact format for additional quotes
            lines.append(f'- "{quote.text}" [{timestamp_str}]')
            if quote.timestamp_link:
                lines[-1] = f'- "{quote.text}" [[{timestamp_str}]({quote.timestamp_link})]'

        lines.append("")

    # Handle case where both summary and quotes are missing
    if not summary and not quotes:
        lines.extend(
            [
                "## Note",
                "",
                (
                    "_No insights were generated for this content. "
                    "This may be due to processing errors or unavailable AI services._"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    """Format timestamp as MM:SS or HH:MM:SS.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
