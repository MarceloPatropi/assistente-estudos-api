import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

from est.features.sync_schedule import Disciplina, TodoList
from ..graph.neo import Graph

class Post(BaseModel):
    id: str
    titulo: str
    conteudo: str
    data: datetime.date
    tipo: str
    acoes_necessarias: Optional[TodoList] = None
    resumo: str
    links: List[str]

class BlogPosts(BaseModel):
    disciplina: Disciplina
    posts: List[Post] = []

def upsert_blog_posts(graph: Graph, periodo: str, curso: str, instituicao: str, blog: BlogPosts):
    disciplina = blog.disciplina
    for post in blog.posts:
        upsert_blog_post(graph, periodo, curso, instituicao, disciplina, post)

def upsert_blog_post(graph: Graph, periodo: str, curso: str, instituicao: str, disciplina: Disciplina, post: Post):
    titulo = post.titulo
    conteudo = post.conteudo
    data = post.data
    tipo = post.tipo
    resumo = post.resumo
    campus = disciplina.campus if disciplina.campus else "Desconhecido"
    sala = disciplina.sala if disciplina.sala else "Desconhecida"
    professor = disciplina.professor if disciplina.professor else "Desconhecido"
    q = '''
        MERGE (inst:INSTITUICAO {nome:$instituicao})
            ON CREATE SET inst.id = randomUUID()
        MERGE (inst)-[:TEM_CAMPUS]->(campus:CAMPUS {nome:$campus})
            ON CREATE SET campus.id = randomUUID()
        MERGE (inst)-[:TEM_CURSO]->(curso:CURSO {nome:$curso})
            ON CREATE SET curso.id = randomUUID()
        MERGE (curso)-[:TEM_PERIODO]->(periodo:PERIODO {nome:$periodo})
            ON CREATE SET periodo.id = randomUUID()
        MERGE (periodo)-[:TEM_DISCIPLINA]->(d:DISCIPLINA {codigo:$disciplina_codigo})
            ON CREATE SET   d.id = randomUUID(), 
                            d.nome = $disciplina_nome,
                            d.professor = $professor,
                            d.campus = $campus,
                            d.sala = $sala
            ON MATCH  SET   d.professor = coalesce($professor, d.professor),
                            d.campus = coalesce($campus, d.campus),
                            d.sala = coalesce($sala, d.sala)
        MERGE (d)-[:OFERECIDO_EM]->(p)
        MERGE (d)-[:PERTENCE_A]->(c)
        MERGE (d)-[:OFERECIDO_POR]->(i)
        MERGE (b:BlogPost {titulo: $titulo, data: $data})-[:RELACIONADO_A]->(d)
            ON CREATE SET 
                b.id = randomUUID(),
                b.tipo = $tipo,
                b.conteudo = $conteudo,
                b.resumo = $resumo
        '''

    params = ({
        "disciplina_nome": disciplina.nome,
        "disciplina_codigo": disciplina.codigo,
        "campus": campus,
        "professor": professor,
        "sala": sala,
        "periodo": periodo,
        "curso": curso,
        "instituicao": instituicao,
        "titulo": titulo,
        "conteudo": conteudo,
        "data": data,
        "tipo": tipo,
        "resumo": resumo
    })

    if post.acoes_necessarias and post.acoes_necessarias.items:
        for idx, acao in enumerate(post.acoes_necessarias.items):
            q += f'''
                    CREATE (a{idx}:AcaoNecessaria {{descricao: $acao_descricao_{idx}, prazo: $acao_prazo_{idx}}})
                    MERGE (b)-[:REQUER_ACAO]->(a{idx})
            '''
            params[f"acao_descricao_{idx}"] = acao.descricao
            params[f"acao_prazo_{idx}"] = acao.prazo

    # graph.run(q, disciplina_nome=disciplina.nome, disciplina_codigo=disciplina.codigo, campus=campus, professor=professor, sala=sala, periodo=periodo, curso=curso, instituicao=instituicao,
    #                  titulo=titulo, conteudo=conteudo, data=data, tipo=tipo, resumo=resumo)

    print(f"Upserting blog post: {post.titulo} for discipline {disciplina.nome}")
    graph.run(q, **params)
