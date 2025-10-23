"""
Amplifier App: Transcribe

Turn videos into searchable transcripts with AI-powered insights.
"""

__version__ = "0.1.0"

from .formatter import format_transcript
from .insights import Quote, QuoteExtractor, Summary, SummaryGenerator, generate_insights
from .pipeline import TranscriptionPipeline
from .state import PipelineState, StateManager, VideoProcessingResult
from .storage import TranscriptStorage

__all__ = [
    "__version__",
    "format_transcript",
    "generate_insights",
    "Quote",
    "QuoteExtractor",
    "Summary",
    "SummaryGenerator",
    "TranscriptionPipeline",
    "PipelineState",
    "StateManager",
    "VideoProcessingResult",
    "TranscriptStorage",
]
