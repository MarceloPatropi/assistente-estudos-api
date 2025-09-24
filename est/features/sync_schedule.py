import datetime
from typing import Annotated, List, Dict, Any, Literal, Optional

from pydantic import BaseModel, Field, computed_field

from ..graph.neo import Graph

WEEKDAYS_PT: tuple[Literal['domingo','segunda','terça','quarta','quinta','sexta','sábado'], ...] = (
    'domingo','segunda','terça','quarta','quinta','sexta','sábado'
)

TimeHHMM = Annotated[str, Field(pattern=r'^\d{2}:\d{2}$')]

class TimeBlock(BaseModel):
    title: str
    start: TimeHHMM
    end: TimeHHMM

class Weekday(BaseModel):
    weekday: Annotated[int, Field(ge=0, le=6)]
    time_blocks: List[TimeBlock] = Field(default_factory=list)

    @computed_field  # incluído no .model_dump()/JSON
    @property
    def weekday_name(self) -> Literal['domingo','segunda','terça','quarta','quinta','sexta','sábado']:
        return WEEKDAYS_PT[self.weekday]

class WeekSchedule(BaseModel):
    week: Optional[Annotated[int, Field(ge=0, le=52)]] = None
    events: List[Weekday] = Field(default_factory=list)

class CalendarEvent(BaseModel):
    id: str
    data: datetime.date
    titulo: str
    start: Optional[TimeHHMM] = None
    end:   Optional[TimeHHMM] = None
    source: List[str] = Field(default_factory=list)
    
class Schedule(BaseModel):
    items: List[CalendarEvent]

class Disciplina(BaseModel):
    nome: str
    codigo: str
    professor: Optional[str] = None
    campus: Optional[str] = None
    sala: Optional[str] = None
    aulas: List[Weekday] = Field(default_factory=list)

class DisciplinasSchedule(BaseModel):
    disciplinas: List[Disciplina] = Field(default_factory=list)

def upsert_schedule(graph: Graph, periodo: str, curso: str, instituicao: str, disciplinas: DisciplinasSchedule):
    print("Upserting schedule...")
    print(f"Periodo: {periodo}, Curso: {curso}, Instituição: {instituicao}")
#    graph.upsert_periodo(periodo, curso, instituicao)
    
    # Agrupa os horários por disciplina e dia da semana
    grouped = {}
    disciplinas = disciplinas.disciplinas
    for d in disciplinas:
        disciplina_nome = d.nome
        disciplina_codigo = d.codigo
        professor = d.professor
        campus = d.campus or "Principal"
        sala = d.sala
        aulas = d.aulas
        for aula in aulas:
            weekday = aula.weekday
            weekday_name = aula.weekday_name
            blocks = aula.time_blocks
            start = "23:59"
            end = "00:00"
            for block in blocks:
                start = min(start, block.start)
                end = max(end, block.end)

        q = """
            MERGE (inst:INSTITUICAO {nome:$instituicao})
            MERGE (inst)-[:TEM_CAMPUS]->(campus:CAMPUS {nome:$campus})
            MERGE (inst)-[:TEM_CURSO]->(curso:CURSO {nome:$curso})
            MERGE (curso)-[:TEM_PERIODO]->(periodo:PERIODO {nome:$periodo})
            MERGE (periodo)-[:TEM_DISCIPLINA]->(d:DISCIPLINA {codigo:$disciplina_codigo})
                ON CREATE SET   d.nome = $disciplina_nome,
                                d.professor = $professor,
                                d.campus = $campus,
                                d.sala = $sala
                ON MATCH  SET   d.professor = coalesce($professor, d.professor),
                                d.campus = coalesce($campus, d.campus),
                                d.sala = coalesce($sala, d.sala)
            MERGE (d)-[:TEM_DIA_DE_AULA]->(m:WEEKDAY {weekday:$weekday})
                ON CREATE SET m.weekday=$weekday, m.weekday_name=$weekday_name
            MERGE (m)-[:TEM_HORARIO]->(h:HORARIO {start:$start, end:$end})
            RETURN m
            """
        graph.run(q, instituicao=instituicao, campus=campus, curso=curso, periodo=periodo, disciplina_codigo=disciplina_codigo, disciplina_nome=disciplina_nome, professor=professor, weekday=weekday, weekday_name=weekday_name, start=start, end=end, sala=sala)
        print(f"  {disciplina_codigo} {disciplina_nome} - {weekday_name} {start}-{end} sala: {sala or '-'}")

