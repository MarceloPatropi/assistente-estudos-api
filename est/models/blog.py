from datetime import date
from typing import List, Optional
from pydantic import AnyHttpUrl, BaseModel, Field, StrictStr

from est.features.sync_schedule import Disciplina
from est.models.todo import TodoList


class Post(BaseModel):
    id: str
    titulo: str
    conteudo: str
    data: Optional[date] = Field(
        default=None,
        description="Post date in format YYYY-MM-DD.",
    )
    tipo: str
    acoes_necessarias: Optional[TodoList] = None
    resumo: str
    links: List[str]

class BlogPosts(BaseModel):
    base_url: Optional[StrictStr] = None
    disciplina: Disciplina
    posts: List[Post] = []
