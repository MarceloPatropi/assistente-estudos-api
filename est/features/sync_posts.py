import datetime

from est.features.sync_schedule import Disciplina
from est.models.blog import BlogPosts, Post

from ..graph.neo import Graph

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
        MERGE (inst)-[:TEM_CAMPUS]->(campus:CAMPUS {nome:$campus})
        MERGE (inst)-[:TEM_CURSO]->(curso:CURSO {nome:$curso})
        MERGE (curso)-[:TEM_PERIODO]->(periodo:PERIODO {nome:$periodo})
        MERGE (periodo)-[:TEM_DISCIPLINA]->(d:DISCIPLINA {codigo:$disciplina_codigo})
            ON CREATE SET   d.nome = $disciplina_nome,
                            d.campus = $campus,
                            d.sala = $sala
            ON MATCH  SET   d.campus = coalesce($campus, d.campus),
                            d.sala = coalesce($sala, d.sala)
        MERGE (prof:PROFESSOR {nome: $professor})-[:ENSINA]->(d)
        MERGE (d)-[:OFERECIDO_POR]->(curso)
        MERGE (b:BlogPost {titulo: $titulo, data: $data})-[:RELACIONADO_A]->(d)
            ON CREATE SET 
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
            try:
                due_date = datetime.date.fromisoformat(str(acao.due_date))
            except (ValueError, TypeError):
                due_date = datetime.date.today()
            acao.due_date = due_date.strftime("%Y-%m-%d")
            q += f'''
                    MERGE (b)-[:REQUER_ACAO]->(a{idx}:AcaoNecessaria {{descricao: "{acao.description}", due_date: date("{acao.due_date}")}})<-[:REQUER_ACAO]-(d)
            '''

    graph.run(q, disciplina_nome=disciplina.nome, disciplina_codigo=disciplina.codigo, campus=campus, professor=professor, sala=sala, periodo=periodo, curso=curso, instituicao=instituicao,
                titulo=titulo, conteudo=conteudo, data=data, tipo=tipo, resumo=resumo)

    print(f"Upserting blog post: {post.titulo} for discipline {disciplina.nome}")
    graph.run(q, **params)
