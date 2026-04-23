"""Writer Agent — turns analysis insights into plain-language stories for residents."""

import asyncio
from datetime import datetime, timezone
from groq import Groq
from core.config import GROQ_API_KEY, GROQ_MODEL
from core.database import save_story


# Initialize Groq client
_client = Groq(api_key=GROQ_API_KEY)


async def run_writer(analysis: dict) -> dict:
    """
    Generate a plain-language news story from the analysis results.
    Save the story to ChromaDB and return the story dict.
    """
    title_input = analysis.get("title", "Untitled")
    key_finding = analysis.get("key_finding", "")
    who_affected = analysis.get("who_affected", "")
    practical_implication = analysis.get("practical_implication", "")
    topic = analysis.get("topic", "economy")
    source_url = analysis.get("source_url", "")
    dataset_id = analysis.get("dataset_id", "")

    # Generate the story body
    story_body = await _generate_story(title_input, key_finding, who_affected, practical_implication)

    # Generate a short headline
    story_title = await _generate_headline(story_body)

    # Save to database
    save_story(
        title=story_title,
        body=story_body,
        topic=topic,
        source_url=source_url,
        dataset_id=dataset_id,
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "title": story_title,
        "body": story_body,
        "topic": topic,
        "source_url": source_url,
        "date": today,
    }

    print(f"Writer Agent: Story created — {story_title}")
    return result


async def _call_groq(prompt: str, label: str) -> str | None:
    """Call Groq with retry logic for rate limits."""
    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < 2:
                wait = (attempt + 1) * 15
                print(f"Writer Agent: Rate limited on {label}, retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"Writer Agent: Groq error {label} — {e}")
                return None
    return None


async def _generate_story(title: str, key_finding: str, who_affected: str, practical_implication: str) -> str:
    """Generate a 120-150 word plain-language story using Groq."""
    prompt = f"""You are a writer for a public information service in Luxembourg.
Write a short news story (120-150 words) based on this data analysis.

Dataset: {title}
Key finding: {key_finding}
Who is affected: {who_affected}
Practical implication: {practical_implication}

Rules for your writing:
- Write in plain English that a non-expert can understand
- Start with the most important fact as the first sentence
- Use specific numbers from the analysis
- Include one practical action or takeaway for the reader
- Do NOT use words like: leverage, unlock, empower, dive deep, game-changer, seamlessly, cutting-edge, robust
- Do NOT mention AI, algorithms, or data processing
- Write as if a journalist wrote it, not an AI
- End with one sentence explaining where readers can find the full data
- Maximum 150 words"""

    result = await _call_groq(prompt, "generating story")
    if result:
        return result

    return (
        f"New data has been published about {title.lower()} in Luxembourg. "
        f"{key_finding} {who_affected} {practical_implication} "
        f"For the full dataset, visit data.public.lu."
    )


async def _generate_headline(story_body: str) -> str:
    """Generate a concise news headline (max 10 words) using Groq."""
    prompt = f"Write a news headline (max 10 words) for this story: {story_body[:500]}"

    result = await _call_groq(prompt, "generating headline")
    if result:
        headline = result.strip('"').strip("'")
        words = headline.split()
        if len(words) > 12:
            headline = " ".join(words[:10])
        return headline

    return f"Update: {story_body[:50]}..."
