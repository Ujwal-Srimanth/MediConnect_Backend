from pydantic import BaseModel, Field
from typing import Optional

class Hospital(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=3, max_length=100)
    location: str = Field(..., min_length=3, max_length=100)
    mobile: str = Field(...,min_length=14)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "HSP001",
                "name": "Apollo Hospitals",
                "location": "Hyderabad"
            }
        }
