from backend.rag.chunker import chunk_text


def test_chunker_produces_chunks():
    page_texts = [(1, "one two three four five six seven eight nine ten")]
    chunks = chunk_text(page_texts, chapter="Test", subtopic=None, chunk_size=4, overlap=1)
    assert len(chunks) >= 2
