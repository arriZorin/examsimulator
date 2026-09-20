import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from question_imports.extractors import ExtractionError, extract_text
from question_imports.parser import parse_questions

VALID = """QUESTION: Capital of France?
OPTION: Berlin
OPTION: Paris
OPTION: Rome
OPTION: Madrid
OPTION: Lisbon
ANSWER: 2
EXPLANATION: Paris is correct.
"""


def test_parser_accepts_four_or_more_options():
    result = parse_questions(VALID)
    assert not result.errors
    assert len(result.questions[0].options) == 5
    assert result.questions[0].correct_index == 2


def test_parser_reports_too_few_options():
    result = parse_questions("""QUESTION: Bad?
OPTION: A
OPTION: B
ANSWER: 1""")
    assert "at least four" in result.errors[0].message.lower()


def test_parser_supports_multiline_explanations_and_more_than_four_options():
    result = parse_questions("""QUESTION: Pick the vowel
OPTION: B
OPTION: C
OPTION: A
OPTION: D
OPTION: F
ANSWER: 3
EXPLANATION: A is a vowel.
It is the only vowel listed.
""")
    assert result.errors == []
    assert len(result.questions[0].options) == 5
    assert result.questions[0].explanation == "A is a vowel.\nIt is the only vowel listed."


def test_parser_accepts_numbered_questions_and_lettered_options():
    result = parse_questions("""1. The students must keep their classroom tidy.
a. dirty
b. clean and neat
c. crowded
d. noisy
answer: 2

2. Arrange these sentences into a logical paragraph:
1) First sentence. 2) Second sentence.
a. 1-2
b. 2-1
c. neither
d. both
answer: 1
""")

    assert result.errors == []
    assert len(result.questions) == 2
    assert result.questions[0].text == "The students must keep their classroom tidy."
    assert result.questions[0].options == ["dirty", "clean and neat", "crowded", "noisy"]
    assert result.questions[0].correct_index == 2
    assert result.questions[1].text.endswith("1) First sentence. 2) Second sentence.")


def test_parser_rejects_duplicate_answer_and_out_of_range_answer():
    result = parse_questions("""QUESTION: Bad answer
OPTION: A
OPTION: B
OPTION: C
OPTION: D
ANSWER: 5
ANSWER: 1
""")
    messages = " ".join(error.message for error in result.errors)
    assert "only appear once" in messages


def test_txt_extractor_supports_utf8_bom():
    upload = SimpleUploadedFile("questions.txt", ("\ufeff" + VALID).encode("utf-8"))
    assert extract_text(upload).startswith("QUESTION:")


def test_unsupported_file_is_rejected():
    with pytest.raises(ExtractionError):
        extract_text(SimpleUploadedFile("questions.exe", b"bad"))
