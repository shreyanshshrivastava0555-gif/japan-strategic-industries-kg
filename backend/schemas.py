"""Pydantic request/response models for the API."""
from typing import List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class PathModel(BaseModel):
    nodes: List[str]
    steps: List[str]


class AskResponse(BaseModel):
    question: str
    answer: str
    summary: str = ""
    entities: List[str] = []
    paths: List[PathModel] = []
    facts: List[str] = []
    mode: str = "offline"
    cached: bool = False


class FetchRequest(BaseModel):
    query: Optional[str] = Field(None, max_length=200)
    per_query: int = Field(6, ge=1, le=20)
    fresh: bool = False
