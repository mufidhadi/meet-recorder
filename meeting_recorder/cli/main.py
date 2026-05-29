import asyncio
import sys
import threading
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from meeting_recorder.config.settings import Settings
from meeting_recorder.capture.windows import WindowsCaptureEngine
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.processing.chunker import AudioChunker
from meeting_recorder.transcription.gemini_transcriber import GeminiTranscriber
from meeting_recorder.ai.aggregator import TranscriptAggregator
from meeting_recorder.ai.gemini import GeminiSummarizer
from meeting_recorder.output.manager import OutputManager

app = typer.Typer(help="Meet-Recorder: AI-powered meeting recording and summarization.")
console = Console()

@app.command()
def devices():
    """List available audio devices."""
    from scratch.check_audio_devices import list_wasapi_devices
    list_wasapi_devices()

@app.command()
def status():
    """Show current meeting detection scores."""
    from meeting_recorder.detection.meeting_detector import MeetingDetector
    settings = Settings()
    detector = MeetingDetector(sample_rate=settings.audio.sample_rate)
    
    # We need a small audio sample for the analyzer
    console.print("[dim]Analyzing environment (3s)...[/dim]")
    # Note: status command is simplified and won't have real audio unless we start engine
    # For now, let's just show Process, Window, and Network
    
    result = detector.detect_once()
    
    table = Table(title="Meeting Detection Status")
    table.add_column("Signal", style="cyan")
    table.add_column("Score", justify="right")
    
    for name, score in result.breakdown.items():
        table.add_row(name.capitalize(), str(score))
        
    table.add_section()
    table.add_row("[bold]Total Score[/bold]", f"[bold]{result.total_score}[/bold]")
    table.add_row("[bold]State[/bold]", f"[bold yellow]{result.state.value}[/bold yellow]")
    
    console.print(table)
    if result.app_detected:
        console.print(f"App Detected: [bold green]{result.app_detected}[/bold green]")

@app.command()
def record(
    chunk_size: float = typer.Option(30.0, help="Duration of each audio chunk in seconds."),
    output_dir: str = typer.Option("./recordings", help="Directory to save recordings.")
):
    """Start recording a meeting manually."""
    settings = Settings()
    if not settings.gemini_api_key:
        console.print("[red]Error: GEMINI_API_KEY not found in .env[/red]")
        raise typer.Exit(1)

    asyncio.run(_record_async(settings, chunk_size, output_dir))

@app.command()
def auto(
    chunk_size: float = typer.Option(30.0, help="Duration of each audio chunk in seconds."),
    output_dir: str = typer.Option("./recordings", help="Directory to save recordings."),
    interval: int = typer.Option(10, help="Interval to check for meetings in seconds.")
):
    """Wait for a meeting to start and record automatically."""
    settings = Settings()
    if not settings.gemini_api_key:
        console.print("[red]Error: GEMINI_API_KEY not found in .env[/red]")
        raise typer.Exit(1)

    from meeting_recorder.detection.meeting_detector import MeetingDetector, MeetingState
    
    recording_task = None
    stop_event = None
    
    def on_meeting_start():
        nonlocal recording_task, stop_event
        if recording_task is None or recording_task.done():
            console.print("[bold green]🎙 Meeting detected! Starting automatic recording...[/bold green]")
            stop_event = asyncio.Event()
            recording_task = asyncio.create_task(_record_async(settings, chunk_size, output_dir, external_stop_event=stop_event))

    def on_meeting_end():
        nonlocal stop_event
        if stop_event:
            console.print("[bold yellow]⏹ Meeting ended. Stopping recording...[/bold yellow]")
            stop_event.set()

    detector = MeetingDetector(
        sample_rate=settings.audio.sample_rate,
        poll_interval_s=interval,
        on_meeting_start=on_meeting_start,
        on_meeting_end=on_meeting_end,
    )
    
    # We need to bridge the audio from engine to detector
    # But in auto mode, the engine is only running when recording.
    # To detect via audio ALWAYS, we would need the engine running always.
    # For MVP auto mode, we rely on Process/Window/Network to START, 
    # and then Audio/Process/Window to MAINTAIN or STOP.
    
    console.print(Panel("Meet-Recorder [bold cyan]AUTO MODE[/bold cyan]\nWatching for meetings in background...", title="Auto-Detect"))

    async def monitor():
        try:
            while True:
                detector.detect_once()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    async def run():
        m_task = asyncio.create_task(monitor())
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            m_task.cancel()
            if stop_event:
                stop_event.set()
            console.print("\n[bold yellow]Auto mode stopped.[/bold yellow]")

    asyncio.run(run())

async def _record_async(settings: Settings, chunk_size: float, output_dir: str, external_stop_event: Optional[asyncio.Event] = None):
    output_mgr = OutputManager(output_dir)
    session_dir = output_mgr.start_session()
    
    console.print(Panel(f"Session started: [bold green]{session_dir}[/bold green]", title="Meet-Recorder"))
    
    buffer = RingBuffer(maxsize_seconds=chunk_size * 4, sample_rate=settings.audio.sample_rate)
    
    if settings.transcription_engine == "local":
        from meeting_recorder.transcription.local_hf import LocalHFTranscriber
        transcriber = LocalHFTranscriber(model_id=settings.local_model_id)
        console.print(f"[dim]Using Local Model: {settings.local_model_id}[/dim]")
    else:
        transcriber = GeminiTranscriber(api_key=settings.gemini_api_key, model_name=settings.gemini_model_id)
        console.print(f"[dim]Using Gemini Transcription Engine ({settings.gemini_model_id})[/dim]")
        
    aggregator = TranscriptAggregator()
    summarizer = GeminiSummarizer(api_key=settings.gemini_api_key, model_name=settings.gemini_model_id)
    
    pending_tasks = set()
    chunk_index = 0
    loop = asyncio.get_running_loop()
    stop_event = external_stop_event or asyncio.Event()
    
    # Auto-stop state
    consecutive_silent_chunks = 0
    MAX_SILENT_CHUNKS = 6 
    last_transcribed_text = ""
    
    def on_chunk_ready(wav_bytes, is_silent: bool):
        nonlocal chunk_index, consecutive_silent_chunks, last_transcribed_text
        
        # 1. Base silence (RMS energy below threshold)
        if is_silent:
            consecutive_silent_chunks += 1
            console.print(f"[dim]Chunk skipped (Low Energy {consecutive_silent_chunks}/{MAX_SILENT_CHUNKS})[/dim]")
            if consecutive_silent_chunks >= MAX_SILENT_CHUNKS:
                console.print("[bold red]Auto-stopping due to inactivity...[/bold red]")
                loop.call_soon_threadsafe(stop_event.set)
            return

        idx = chunk_index
        chunk_index += 1
        
        async def handle_and_check_hallucination():
            nonlocal consecutive_silent_chunks, last_transcribed_text
            try:
                result = await _handle_chunk(idx, wav_bytes, transcriber, aggregator, output_mgr, chunk_size)
                
                # result can be None if _handle_chunk caught an exception
                if result is None:
                    return

                # 2. Hallucination detection (Repetitive text)
                current_text = result.full_text.strip()
                if current_text and current_text == last_transcribed_text:
                    consecutive_silent_chunks += 1
                    console.print(f"[dim]Repetitive text detected ({consecutive_silent_chunks}/{MAX_SILENT_CHUNKS})[/dim]")
                    if consecutive_silent_chunks >= MAX_SILENT_CHUNKS:
                         console.print("[bold red]Auto-stopping due to repetitive hallucinations...[/bold red]")
                         stop_event.set()
                else:
                    # Clear text if it's new/meaningful
                    if current_text:
                        consecutive_silent_chunks = 0
                        last_transcribed_text = current_text
            except Exception as e:
                console.print(f"[red]Error in processing task: {e}[/red]")

        # Dispatch transcription task safely from background thread
        def start_task():
            task = asyncio.create_task(handle_and_check_hallucination())
            pending_tasks.add(task)
            task.add_done_callback(pending_tasks.discard)
            
        loop.call_soon_threadsafe(start_task)

    engine = WindowsCaptureEngine(settings.audio, callback=buffer.push)
    chunker = AudioChunker(
        buffer, 
        chunk_duration_s=chunk_size, 
        on_chunk_callback=on_chunk_ready,
        silence_threshold=settings.silence_threshold
    )

    try:
        engine.start()
        chunker.start()
        console.print("[yellow]Recording... Press Ctrl+C to stop.[/yellow]")
        
        # Wait for stop event or Ctrl+C
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[bold yellow]Interrupted. Cleaning up...[/bold yellow]")
    finally:
        # ENSURE CLEANUP AND SUMMARIZATION RUNS
        console.print("[bold yellow]Stopping engine and chunker...[/bold yellow]")
        engine.stop()
        chunker.stop()
        
        if pending_tasks:
            console.print(f"Waiting for {len(pending_tasks)} pending transcriptions...")
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            
        full_text = aggregator.get_full_transcript()
        
        if full_text.strip():
            console.print("[bold blue]Generating final summary...[/bold blue]")
            try:
                summary = await summarizer.summarize(full_text)
                output_mgr.save_summary(summary.raw_markdown)
                console.print(Panel(f"Meeting Summary: [bold white]{summary.title}[/bold white]\n\nAll files saved to {session_dir}", title="Success"))
            except Exception as e:
                console.print(f"[red]Error generating summary: {e}[/red]")
        else:
            console.print("[yellow]No transcript generated, skipping summary.[/yellow]")
        
        # Final save of transcript
        output_mgr.save_transcript(aggregator.all_segments, full_text)
        console.print(f"[green]Session folder: {session_dir}[/green]")

async def _handle_chunk(idx: int, wav_bytes: bytes, transcriber, aggregator, output_mgr, chunk_size: float):
    try:
        # Calculate offset
        offset = idx * chunk_size 
        result = await transcriber.transcribe(wav_bytes)
        aggregator.add_result(result, offset_s=offset)
        output_mgr.save_audio_chunk(idx, wav_bytes)
        
        # Incremental Save
        full_text = aggregator.get_full_transcript()
        output_mgr.save_transcript(aggregator.all_segments, full_text)
        
        console.print(f"[dim]Chunk {idx} transcribed: {result.full_text[:75]}...[/dim]")
        return result
    except Exception as e:
        console.print(f"[red]Error transcribing chunk {idx}: {e}[/red]")
        return None

if __name__ == "__main__":
    app()
