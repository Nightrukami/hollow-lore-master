import json
from pathlib import Path
from pydantic import BaseModel, Field

TEST_DIR = Path(__file__).parent


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="The question to ask the RAG system")
    keywords: list[str] = Field(description="Keywords that must appear in retrieved context")
    reference_answer: str = Field(description="The reference answer for this question")
    category: str = Field(description="Question category (e.g., direct_fact, spanning, temporal)")


def load_tests(filename: str = "tests.jsonl") -> list[TestQuestion]:
    """Load test questions from a JSONL file in this directory."""
    tests = []
    with open(TEST_DIR / filename, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
