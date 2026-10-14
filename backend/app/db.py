from sqlmodel import SQLModel, Field
from typing import Optional

class Task(SQLModel, table=True):
    id: str = Field(primary_key=True)
    status: str
    input_image_url: Optional[str] = None
    reference_image_url: Optional[str] = None
    top_text: Optional[str] = None
    bottom_text: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[str] = None
