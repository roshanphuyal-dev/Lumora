import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRagStatus
from app.models.notebook import Notebook, NotebookSource
from app.models.rag import Chunk, Embedding, SectionLocatorKind
from app.models.user import User
from app.services.rag_retrieval_service import (
    MAX_CONTEXT_CHARS,
    MAX_RESULTS,
    RetrievalCandidate,
    _text_search,
    _vector_search,
    assemble_grounding,
    fuse_results,
    retrieve,
)


def candidate(
    value: int, *, text: str = "text", vector: float | None = None, rank: float | None = None
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=uuid.UUID(int=value),
        source_id=uuid.UUID(int=100 + value),
        document_id=uuid.UUID(int=200 + value),
        source_title=f"Source {value}",
        text=text,
        locator_kind=SectionLocatorKind.PAGE,
        locator=value,
        vector_similarity=vector,
        text_rank=rank,
    )


def test_rrf_rewards_overlap_and_deduplicates_chunks() -> None:
    fused = fuse_results(
        [candidate(1, vector=0.9), candidate(2, vector=0.8)],
        [candidate(2, rank=0.7), candidate(3, rank=0.6)],
    )

    assert [item.chunk_id for item in fused] == [
        uuid.UUID(int=2),
        uuid.UUID(int=1),
        uuid.UUID(int=3),
    ]
    assert len({item.chunk_id for item in fused}) == 3
    assert fused[0].vector_similarity == 0.8
    assert fused[0].text_rank == 0.7


def test_checked_in_retrieval_eval_fixture_keeps_relevant_chunks_in_top_three() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "rag_retrieval_eval.json"
    cases = json.loads(fixture_path.read_text())["cases"]

    for case in cases:
        vector_results = [
            candidate(uuid.UUID(chunk_id).int, vector=1 - rank / 100)
            for rank, chunk_id in enumerate(case["vector_ranking"], start=1)
        ]
        text_results = [
            candidate(uuid.UUID(chunk_id).int, rank=1 - rank / 100)
            for rank, chunk_id in enumerate(case["text_ranking"], start=1)
        ]

        top_three = {str(item.chunk_id) for item in fuse_results(vector_results, text_results)[:3]}

        assert top_three.intersection(case["relevant_chunk_ids"]), case["query"]


def test_context_and_citations_are_bounded_and_authoritative() -> None:
    candidates = [candidate(index, text="x" * 3000) for index in range(1, 12)]
    grounding = assemble_grounding(candidates)

    assert len(grounding.results) <= MAX_RESULTS
    assert len(grounding.context) <= MAX_CONTEXT_CHARS
    assert [citation.chunk_id for citation in grounding.citations] == [
        str(item.chunk_id) for item in grounding.results
    ]
    assert all(len(citation.excerpt or "") <= 500 for citation in grounding.citations)
    assert grounding.citations[0].source_title == "Source 1"
    assert grounding.citations[0].locator_kind == "page"


async def test_vector_and_text_search_are_notebook_and_owner_scoped(
    db_session: AsyncSession,
) -> None:
    owners = [
        User(email=f"retrieval-{index}@example.com", full_name=f"Owner {index}")
        for index in range(2)
    ]
    db_session.add_all(owners)
    await db_session.flush()
    notebooks = [
        Notebook(owner_id=owner.id, name=f"Notebook {index}") for index, owner in enumerate(owners)
    ]
    db_session.add_all(notebooks)
    await db_session.flush()

    for index, (owner, notebook) in enumerate(zip(owners, notebooks, strict=True)):
        document = Document(
            uploaded_by=owner.id,
            filename=f"source-{index}.pdf",
            storage_path=f"source-{index}.pdf",
            mime_type="application/pdf",
            file_type="pdf",
            rag_status=DocumentRagStatus.INDEXED,
        )
        db_session.add(document)
        await db_session.flush()
        source = NotebookSource(notebook_id=notebook.id, document_id=document.id)
        chunk = Chunk(
            document_id=document.id,
            ordinal=1,
            text="mitochondria respiration owner " + str(index),
            content_hash=str(index) * 64,
        )
        db_session.add_all([source, chunk])
        await db_session.flush()
        db_session.add(
            Embedding(
                chunk_id=chunk.id,
                vector=[1.0] + [0.0] * 767,
                model="gemini-embedding-001",
                model_version="001",
                dimensions=768,
            )
        )
    await db_session.commit()

    vector = await _vector_search(db_session, owners[0].id, notebooks[0].id, [1.0] + [0.0] * 767)
    text = await _text_search(db_session, owners[0].id, notebooks[0].id, "mitochondria")

    assert len(vector) == 1
    assert len(text) == 1
    assert vector[0].source_title == "source-0.pdf"
    assert text[0].source_title == "source-0.pdf"


async def test_retrieve_skips_embedding_without_indexed_local_content(
    db_session: AsyncSession,
) -> None:
    with patch("app.services.rag_retrieval_service.run_task", new_callable=AsyncMock) as run_task:
        grounding = await retrieve(db_session, uuid.uuid4(), uuid.uuid4(), "question")

    run_task.assert_not_awaited()
    assert grounding.results == []
    assert grounding.context == ""
    assert grounding.citations == []
