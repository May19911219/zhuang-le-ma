from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


class PlanRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    platform: str


class FeedbackRequest(BaseModel):
    verdict: str
    content: str = ""


class LoginRequest(BaseModel):
    password: str


class PlanUpdateRequest(BaseModel):
    markdown: str
    script: str = ""


class FeedbackStatusRequest(BaseModel):
    status: str
