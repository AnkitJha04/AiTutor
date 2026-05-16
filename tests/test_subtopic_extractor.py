from backend.services.subtopic_extractor import extract_subtopics


def test_extract_subtopics_from_headings():
    text = """
    1 Introduction
    This is a sample.
    1.1 Subsection
    More content.
    """
    result = extract_subtopics(text)
    assert result
    assert result[0]["title"].startswith("1 Introduction")
