from typing import Literal
from pydantic import BaseModel, Field, SecretStr, field_validator


def normalize_llm_model(value):
    value = value.strip()
    if value.lower() == "deepseek":
        return "deepseek/deepseek-flash"
    if not value or "/" not in value or not all(value.split("/", 1)):
        raise ValueError("请填写完整的 LLM 模型名称，例如 deepseek/deepseek-flash。")
    return value


class Parameters(BaseModel):
    ecut: float = Field(20, gt=0, le=500)
    mesh: tuple[int, int, int] = (2, 2, 2)
    nbnd: int = Field(14, ge=1, le=10000)
    points_per_segment: int = Field(20, ge=2, le=500)
    functional: Literal["PBE", "LDA"] = "PBE"
    smear: Literal["gaussian"] = "gaussian"

    @field_validator("mesh")
    @classmethod
    def positive_mesh(cls, v):
        if any(n < 1 or n > 64 for n in v):
            raise ValueError("mesh entries must be in 1..64")
        return v


class JobRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)
    mp_api_key: SecretStr
    llm_api_key: SecretStr
    material_id: str | None = Field(None, pattern=r"^mp-[0-9]+$")
    parameters: Parameters = Field(default_factory=Parameters)
    mode: Literal["prepare", "run"] = "run"

    @field_validator("mp_api_key", "llm_api_key")
    @classmethod
    def nonempty(cls, v):
        if not v.get_secret_value().strip():
            raise ValueError("API key is empty")
        return v


class FormulaResult(BaseModel):
    formula: str = Field(min_length=1, max_length=100)
