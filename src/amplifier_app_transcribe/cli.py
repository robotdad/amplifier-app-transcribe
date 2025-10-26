"""
Rich CLI Interface for Transcription App

Beautiful command-line interface with progress bars and status updates.
"""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_time=False)],
    )


@click.command()
@click.argument("sources", nargs=-1, required=False)
@click.option("--web", is_flag=True, help="Launch web interface in browser")
@click.option("--resume", is_flag=True, help="Resume from last saved state")
@click.option("--session-dir", type=click.Path(path_type=Path), help="Session directory for state")
@click.option("--output-dir", type=click.Path(path_type=Path), help="Output directory for transcripts")
@click.option("--no-enhance", is_flag=True, help="Skip AI enhancements (summaries/quotes)")
@click.option("--force-download", is_flag=True, help="Skip cache and re-download audio")
@click.option("--index-only", is_flag=True, help="Generate index.md only (no transcription)")
@click.option("--question", "-q", type=str, help="Question to answer in insights overview")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(
    sources: tuple[str] | None,
    web: bool,
    resume: bool,
    session_dir: Path | None,
    output_dir: Path | None,
    no_enhance: bool,
    force_download: bool,
    index_only: bool,
    question: str | None,
    verbose: bool,
):
    """Transcribe videos and audio files with AI-powered insights.

    SOURCES can be YouTube URLs or local file paths.

    Examples:

        transcribe --web  # Launch browser UI

        transcribe https://youtube.com/watch?v=...

        transcribe video.mp4 audio.mp3

        transcribe *.mp4 --resume

        transcribe --index-only  # Generate index only
    """
    # Load environment variables from .env
    load_dotenv()

    # Setup logging
    setup_logging(verbose)

    # Handle web mode
    if web:
        from .web import launch_web_ui

        launch_web_ui(verbose=verbose)
        return  # launch_web_ui blocks until killed

    # Handle index-only mode
    if index_only:
        return _generate_index(output_dir)

    # Require sources for transcription
    if not sources:
        console.print("[red]Error: Provide at least one video URL or audio file[/red]")
        console.print("\nUsage: transcribe URL [URL...] [OPTIONS]")
        console.print("Or: transcribe --index-only")
        sys.exit(1)

    try:
        # Tools are initialized internally by pipeline from git dependencies
        # Verify dependencies are available
        try:
            import amplifier_module_tool_whisper  # type: ignore # noqa: F401
            import amplifier_module_tool_youtube_dl  # type: ignore # noqa: F401
        except ImportError as e:
            console.print(f"[red]Error: Failed to import tools: {e}[/red]")
            console.print("\n[yellow]Make sure tool dependencies are installed:[/yellow]")
            console.print("  uv sync")
            sys.exit(1)

        # Import pipeline components
        from .pipeline import TranscriptionPipeline
        from .state import StateManager

        # Show banner
        console.print(
            Panel.fit(
                "[bold cyan]Transcribe[/bold cyan]\nTurn videos into searchable transcripts with AI-powered insights",
                border_style="cyan",
            )
        )

        # Create state manager
        state_manager = StateManager(session_dir) if session_dir else StateManager()

        # Create pipeline with enhancement setting
        # Tools initialized internally by pipeline
        enhance = not no_enhance
        pipeline = TranscriptionPipeline(
            state_manager=state_manager,
            enhance=enhance,
            force_download=force_download,
            question=question,
        )

        # Override output directory if specified
        if output_dir:
            pipeline.storage.output_dir = Path(output_dir).expanduser()
            pipeline.storage.output_dir.mkdir(parents=True, exist_ok=True)

        # Show configuration
        console.print("\n[cyan]Configuration:[/cyan]")
        console.print(f"  Output: {pipeline.storage.output_dir}")
        console.print(f"  AI Insights: {'Enabled' if enhance else 'Disabled'}")
        console.print(f"  Sources: {len(sources)} {'file' if len(sources) == 1 else 'files'}")

        # Run pipeline with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Add overall task
            overall_task = progress.add_task("[cyan]Processing videos...", total=len(sources))

            # Store original logger handlers
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers.copy()

            # Temporarily disable rich logging during processing to show progress bar
            root_logger.handlers = []

            try:
                success = pipeline.run(list(sources), resume=resume)
            finally:
                # Restore logging handlers
                root_logger.handlers = original_handlers
                progress.update(overall_task, completed=len(sources))

        # Show results
        _show_results(pipeline.state, console)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Pipeline interrupted - state saved for resume[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


def _generate_index(output_dir: Path | None = None) -> int:
    """Generate index.md for all transcripts (internal helper)."""
    from .storage import TranscriptStorage

    storage = TranscriptStorage(output_dir)

    if not storage.output_dir.exists():
        console.print(f"[red]No transcripts directory found at {storage.output_dir}[/red]")
        sys.exit(1)

    # Count transcript directories
    transcript_dirs = [d for d in storage.output_dir.iterdir() if d.is_dir()]

    if not transcript_dirs:
        console.print(f"[yellow]No transcripts found in {storage.output_dir}[/yellow]")
        sys.exit(0)

    console.print(f"[cyan]Found {len(transcript_dirs)} transcripts[/cyan]")
    console.print(f"[green]✓ Index would be generated at {storage.output_dir / 'index.md'}[/green]")

    # Note: Index generation not implemented in this version
    console.print("\n[yellow]Note: Index generation is not yet implemented[/yellow]")
    console.print("Each transcript directory contains:")
    console.print("  • transcript.md - Formatted transcript")
    console.print("  • insights.md - AI summary and quotes")
    console.print("  • transcript.json - Full data")
    return 0


def _show_results(state, console: Console):
    """Display results summary table."""
    console.print("\n")

    # Create results table
    table = Table(title="Transcription Results", show_header=True, header_style="bold cyan")
    table.add_column("Status", style="dim", width=10)
    table.add_column("Video ID")
    table.add_column("Duration", justify="right")
    table.add_column("Cost", justify="right")

    # Add processed videos
    for result in state.state.processed_videos:
        duration = f"{result.duration_seconds / 60:.1f}m"
        cost = f"${result.cost_estimate:.3f}"
        table.add_row("✓ Success", result.video_id[:50], duration, cost, style="green")

    # Add failed videos
    for result in state.state.failed_videos:
        error = result.error[:30] if result.error else "Unknown error"
        table.add_row("✗ Failed", result.video_id[:50], error, "", style="red")

    console.print(table)

    # Summary statistics
    total = len(state.state.processed_videos)
    failed = len(state.state.failed_videos)

    if total > 0:
        console.print(f"\n[green]✓ Successfully processed {total} {'video' if total == 1 else 'videos'}[/green]")
        console.print(f"  Total Duration: {state.state.total_duration_seconds / 60:.1f} minutes")
        console.print(f"  Estimated Cost: ${state.state.total_cost_estimate:.2f}")

    if failed > 0:
        console.print(f"\n[red]✗ Failed to process {failed} {'video' if failed == 1 else 'videos'}[/red]")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
