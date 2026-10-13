from typing import Literal
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    title: str
    spec: str
    function_signature: str
    difficulty: Literal["easy", "medium", "hard"]
    hidden_tests: str


class WriterOutput(BaseModel):
    code: str
    round_number: int


class Issue(BaseModel):
    category: Literal["correctness", "edge_case", "security", "readability", "performance"]
    severity: Literal["critical", "minor"]
    explanation: str
    suggestion: str


class CritiqueResult(BaseModel):
    verdict: Literal["APPROVE", "REVISE"]
    issues: list[Issue] = Field(default_factory=list)
    summary: str
