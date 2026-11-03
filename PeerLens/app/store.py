from datetime import timedelta
from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from app.config import Settings, get_settings
from app.documents import Chunk


class StoreError(RuntimeError):
    pass


def _connect(settings: Settings | None = None) -> psycopg.Connection[Any]:
    config = settings or get_settings()
    connection = psycopg.connect(config.database_url, connect_timeout=5)
    register_vector(connection)
    return connection


def initialize(settings: Settings | None = None) -> None:
    try:
        with _connect(settings) as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    heading TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    UNIQUE (source, page, chunk_index)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_log (
                    id BIGSERIAL PRIMARY KEY,
                    request_type TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    estimated_cost_usd DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
    except psycopg.Error as error:
        raise StoreError("Could not initialize the PostgreSQL database.") from error


def replace_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("Each document chunk must have exactly one embedding.")
    if not chunks:
        return
    try:
        with _connect() as connection:
            connection.executemany(
                """
                INSERT INTO document_chunks
                    (source, page, heading, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, page, chunk_index) DO UPDATE SET
                    heading = EXCLUDED.heading,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
                """,
                [
                    (
                        chunk.source,
                        chunk.page,
                        chunk.heading,
                        chunk.index,
                        chunk.content,
                        embedding,
                    )
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ],
            )
    except psycopg.Error as error:
        raise StoreError("Could not store document chunks.") from error


def search_chunks(embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT source, page, heading, content,
                       1 - (embedding <=> %s) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (embedding, embedding, limit),
            ).fetchall()
    except psycopg.Error as error:
        raise StoreError("Could not search document chunks.") from error
    return [
        {
            "source": row[0],
            "page": row[1],
            "heading": row[2],
            "content": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]


def log_usage(
    request_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float | None,
) -> None:
    try:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_log
                    (request_type, model, input_tokens, output_tokens, estimated_cost_usd)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (request_type, model, input_tokens, output_tokens, estimated_cost_usd),
            )
    except psycopg.Error as error:
        raise StoreError("Could not record model usage.") from error


def usage_summary(days: int = 30) -> list[dict[str, Any]]:
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT request_type, model, COUNT(*), SUM(input_tokens),
                       SUM(output_tokens), SUM(estimated_cost_usd)
                FROM usage_log
                WHERE created_at >= NOW() - %s
                GROUP BY request_type, model
                ORDER BY request_type, model
                """,
                (timedelta(days=days),),
            ).fetchall()
    except psycopg.Error as error:
        raise StoreError("Could not retrieve usage data.") from error
    return [
        {
            "request_type": row[0],
            "model": row[1],
            "requests": row[2],
            "input_tokens": row[3],
            "output_tokens": row[4],
            "estimated_cost_usd": float(row[5]) if row[5] is not None else None,
        }
        for row in rows
    ]
