"""Scheduler — orchestrates the three-agent pipeline and manages recurring runs."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agents.monitor_agent import run_monitor
from agents.analysis_agent import run_analysis
from agents.writer_agent import run_writer


_scheduler: AsyncIOScheduler | None = None
_pipeline_running = False
_last_run_time = ""


async def run_pipeline() -> int:
    """
    Execute the full pipeline:
    1. Monitor agent finds changed datasets
    2. Analysis agent extracts insights from each
    3. Writer agent generates stories from each analysis
    Returns the count of stories generated.
    """
    global _pipeline_running, _last_run_time
    from datetime import datetime, timezone

    if _pipeline_running:
        print("Pipeline: Already running, skipping this invocation.")
        return 0

    _pipeline_running = True
    stories_count = 0

    try:
        print("Pipeline: Starting run...")

        # Step 1 — Monitor
        changed_datasets = await run_monitor()
        if not changed_datasets:
            print("Pipeline: No changed datasets found.")
            _last_run_time = datetime.now(timezone.utc).isoformat()
            return 0

        # Step 2 & 3 — Analysis + Writer (with rate-limit delay)
        for i, dataset in enumerate(changed_datasets):
            try:
                analysis = await run_analysis(dataset)

                # Step 3 — Writer
                story = await run_writer(analysis)
                if story:
                    stories_count += 1

                # Delay between datasets to respect Gemini free-tier rate limits
                if i < len(changed_datasets) - 1:
                    await asyncio.sleep(4)
            except Exception as e:
                print(f"Pipeline: Error processing dataset '{dataset.get('title', 'unknown')}' — {e}")
                continue

        _last_run_time = datetime.now(timezone.utc).isoformat()
        print(f"Pipeline complete. {stories_count} new stories generated.")

    except Exception as e:
        print(f"Pipeline: Critical error — {e}")
    finally:
        _pipeline_running = False

    return stories_count


def start_scheduler() -> None:
    """Start the APScheduler to run the pipeline every 6 hours."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(run_pipeline, "interval", hours=6, id="pipeline_job")
    _scheduler.start()
    print("Scheduler: Started. Pipeline will run every 6 hours.")


def get_last_run_time() -> str:
    """Return the ISO timestamp of the last pipeline run."""
    return _last_run_time


def is_pipeline_running() -> bool:
    """Check if the pipeline is currently running."""
    return _pipeline_running
