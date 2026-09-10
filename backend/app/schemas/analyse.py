from pydantic import BaseModel


class AnalyseRequest(BaseModel):
    text: str
