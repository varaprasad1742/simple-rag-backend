from pydantic import BaseModel


class ChatRequest(
    BaseModel
):

    query: str


class Citation(
    BaseModel
):
    id: int

    document_id : str 

    content: str 
    
    filename: str

    start_page: int

    end_page: int


class ChatResponse(
    BaseModel
):
    

    answer: str

    citations: list[Citation]


class CreateChatRequest(
    BaseModel
):

    title: str