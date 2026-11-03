import asyncio
from pathlib import Path

from app.config import get_settings
from app.documents import chunk_pages, parse_filing
from app.llm import LLMClient, estimate_cost
from app.store import initialize, log_usage, replace_chunks


async def ingest() -> None:
    settings = get_settings()
    client = LLMClient(settings)
    initialize(settings)
    files = sorted(Path("data/raw").glob("*.htm*"))
    if not files:
        raise FileNotFoundError("No HTML filings found in data/raw.")

    for path in files:
        pages = parse_filing(path)
        chunks = chunk_pages(
            path.name,
            pages,
            max_chars=settings.chunk_size_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        for start in range(0, len(chunks), 64):
            batch = chunks[start : start + 64]
            embeddings, usage = await client.embeddings([chunk.content for chunk in batch])
            replace_chunks(batch, embeddings)
            log_usage(
                "embedding",
                settings.embedding_model,
                usage["input_tokens"],
                usage["output_tokens"],
                estimate_cost(
                    settings,
                    "embedding",
                    usage["input_tokens"],
                    usage["output_tokens"],
                ),
            )
        print(f"Ingested {path.name}: {len(pages)} pages, {len(chunks)} chunks")


if __name__ == "__main__":
    asyncio.run(ingest())
