from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AthleteProfileBase(BaseModel):
    age: Optional[int] = Field(None, ge=10, le=100)
    gender: Optional[str] = None
    height: Optional[float] = Field(None, ge=50, le=300) # cm
    weight: Optional[float] = Field(None, ge=20, le=300) # kg
    sport: Optional[str] = None
    experience_level: Optional[str] = None

class AthleteProfileCreate(AthleteProfileBase):
    pass

class AthleteProfileUpdate(AthleteProfileBase):
    pass

class AthleteProfileResponse(AthleteProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
