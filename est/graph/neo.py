from neo4j import GraphDatabase
from typing import Optional, Dict, Any, List

class Graph:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run(self, cypher: str, **params):
        with self.driver.session() as session:
            return list(session.run(cypher, **params))

    # --- Schema ---
    def ensure_constraints(self):
        stmts = [
            "CREATE CONSTRAINT course_id IF NOT EXISTS FOR (c:COURSE) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:SECTION) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT periodo_nome IF NOT EXISTS FOR (p:PERIODO) REQUIRE p.nome IS UNIQUE",
            "CREATE CONSTRAINT mp_uid IF NOT EXISTS FOR (m:MEETING_PATTERN) REQUIRE m.uid IS UNIQUE",
            "CREATE CONSTRAINT cal_id IF NOT EXISTS FOR (c:CALENDAR) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT calevent_id IF NOT EXISTS FOR (e:CALENDAR_EVENT) REQUIRE e.id IS UNIQUE",
        ]
        with self.driver.session() as s:
            for q in stmts:
                s.run(q)

    # --- Upserts ---
    def upsert_periodo(self, nome: str, curso: str, instituicao: str, inicio: Optional[str]=None, fim: Optional[str]=None):
        q = '''
        MERGE (p:PERIODO {nome:$nome})-[r:OF_CURSO]->(c:CURSO {nome:$curso})-[i:OF_INSTITUICAO]->(inst:INSTITUICAO {nome:$instituicao})
        ON CREATE SET p.id = randomUUID(), c.id = randomUUID(), inst.id = randomUUID()
        SET p.inicio = coalesce($inicio, p.inicio),
            p.fim = coalesce($fim, p.fim),
            p.id = coalesce(p.id, randomUUID())
        RETURN p
        '''
        return self.run(q, nome=nome, curso=curso, instituicao=instituicao, inicio=inicio, fim=fim)

    def upsert_disciplina(self, periodo: str, curso: str, instituicao: str, disciplina: str, codigo: str):
        q = '''
        MERGE (inst:INSTITUICAO {nome:$instituicao})
            ON CREATE SET inst.id = randomUUID()
        MERGE (c:CURSO {nome:$curso})-[i:OF_INSTITUICAO]->(inst)
            ON CREATE SET c.id = randomUUID()
        MERGE (p:PERIODO {nome:$periodo})-[r:OF_CURSO]->(c)
            ON CREATE SET p.id = randomUUID()
        MERGE (d:DISCIPLINA {nome:$disciplina})<-[:HAS_DISCIPLINA]-(p)
        ON CREATE SET 
            d.id = coalesce(randomUUID(), d.id)
        SET d.codigo = coalesce($codigo, d.codigo)
        RETURN d
        '''
        return self.run(q, periodo=periodo, curso=curso, instituicao=instituicao, disciplina=disciplina, codigo=codigo)

    def upsert_section(self, term_nome: str, course_codigo: str, turma: str, campus: Optional[str]=None):
        q = '''
        MATCH (t:TERM {nome:$term_nome})
        MATCH (c:COURSE {codigo:$course_codigo})
        MERGE (s:SECTION {id:$sid})
          ON CREATE SET s.turma=$turma, s.campus=$campus
          ON MATCH  SET s.turma=coalesce($turma,s.turma), s.campus=coalesce($campus,s.campus)
        MERGE (s)-[:OF_COURSE]->(c)
        MERGE (s)-[:IN_TERM]->(t)
        RETURN s
        '''
        sid = f"{term_nome}:{course_codigo}:{turma}"
        return self.run(q, term_nome=term_nome, course_codigo=course_codigo, turma=turma, campus=campus, sid=sid)

    def upsert_instituicao(self, term_nome: str, course_codigo: str, curso: str, instituicao: Optional[str]=None):
        q = '''
        MATCH (t:TERM {nome:$term_nome})
        MATCH (c:COURSE {codigo:$course_codigo})
        MERGE (s:SECTION {instituicao:$instituicao})
          ON CREATE SET s.curso=$curso, s.instituicao=$instituicao
          ON MATCH  SET s.curso=coalesce($curso,s.curso), s.instituicao=coalesce($instituicao,s.instituicao)
        MERGE (s)-[:OF_COURSE]->(c)
        MERGE (s)-[:IN_TERM]->(t)
        RETURN s
        '''
        sid = f"{term_nome}:{course_codigo}:{curso}"
        return self.run(q, term_nome=term_nome, course_codigo=course_codigo, curso=curso, instituicao=instituicao, sid=sid)

    # --- Queries ---
    def list_patterns(self) -> List[Dict[str,Any]]:
        q = '''
        MATCH (s:SECTION)-[:HAS_PATTERN]->(m:MEETING_PATTERN)
        OPTIONAL MATCH (s)-[:OF_COURSE]->(c:COURSE)
        OPTIONAL MATCH (s)-[:IN_TERM]->(t:TERM)
        RETURN t.nome AS term, c.codigo AS codigo, c.titulo AS titulo,
               s.id AS section_id, s.turma AS turma,
               m.uid AS uid, m.weekday AS weekday, m.start AS start, m.end AS end,
               m.sala AS sala, m.professor AS professor
        ORDER BY codigo, weekday, start
        '''
        rows = self.run(q)
        return [dict(r) for r in rows]
