from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List


class ProfileCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not isinstance(v, str):
            raise ValueError("name must be a string")
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip().lower()



class ProfileResponse(BaseModel):
    id: str
    name: str
    gender: Optional[str]
    gender_probability: Optional[float]
    sample_size: Optional[int]
    age: Optional[int]
    age_group: Optional[str]
    country_id: Optional[str]
    country_probability: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileListItem(BaseModel):
    id: str
    name: str
    gender: Optional[str]
    age: Optional[int]
    age_group: Optional[str]
    country_id: Optional[str]

    model_config = {"from_attributes": True}



class SingleProfileEnvelope(BaseModel):
    status: str
    data: ProfileResponse


class ProfileAlreadyExistsEnvelope(BaseModel):
    status: str
    message: str
    data: ProfileResponse


class ProfileListEnvelope(BaseModel):
    status: str
    count: int
    data: List[ProfileListItem]


class ErrorResponse(BaseModel):
    status: str
    message: str
