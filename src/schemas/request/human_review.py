from pydantic import BaseModel, Field


class HumanReviewResolve(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    priority: str = Field(default="中", pattern="^(紧急|高|中)$")
    note: str = Field(default="", max_length=300)
