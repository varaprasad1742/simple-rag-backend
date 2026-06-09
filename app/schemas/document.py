from pydantic import BaseModel


class DocumentResponse(BaseModel):

    id: str

    filename: str

    status: str

    class Config:
        from_attributes = True