from pydantic import BaseModel, ConfigDict, Field


class SignContractIn(BaseModel):
    length: int = Field(..., ge=1, le=8)
    salary: int = Field(..., ge=750, le=15000)
    no_trade_clause: bool = False


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    length: int
    signed_season_year: int
    expires_after_year: int
    salary: int
    no_trade_clause: bool
    status: str
