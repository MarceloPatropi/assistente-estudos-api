
import typer
from est.features.sync_todo import app as todo_app  # importa o Typer do sync_todo

from rich import print
from .config import (PORTAL_BASE, PORTAL_USER, PORTAL_PASS, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                     OPENAI_MODEL, USE_LLM, LOCAL_TZ)
from .graph.neo import Graph
from .connectors.portal_client import PortalClient
from .parsers.heuristic import parse_schedule_html
from .parsers.llm import parse_with_llm
from .features.sync_schedule import DisciplinasSchedule, upsert_schedule
from .features.sync_posts import BlogPosts, upsert_blog_posts, upsert_blog_post
from .utils.cal_export import patterns_to_ics

from pydantic import BaseModel, Field, computed_field
from typing import Annotated, List, Literal, Optional
import time, calendar, datetime

app = typer.Typer(add_completion=False, help="Assistente de Estudos — CLI")
# registra os subcomandos de To Do sob o nome 'todo'
app.add_typer(todo_app, name="todo")

@app.command()
def setup_graph():
    g = Graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    g.ensure_constraints()
    g.close()
    print("[green]Constraints verificadas/criadas no Neo4j.[/green]")

@app.command()
def pull_schedule(periodo: str = typer.Option("2025/2", help="Período/Semestre"),
                  curso: str = typer.Option("A", help="Curso"),
                  instituicao: str = typer.Option("Universidade", help="Instituição"),
                  visivel: bool = typer.Option(False, help="Abrir navegador visível")):
    if not (PORTAL_USER and PORTAL_PASS):
        raise typer.Exit("Defina PORTAL_USER/PORTAL_PASS no .env")
    g = Graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    Portal = PortalClient(PORTAL_BASE, PORTAL_USER, PORTAL_PASS, headless=not visivel)
    html = Portal.fetch_schedule_html()
    if USE_LLM:
        prompt = """Você recebe HTML soup de grade horária universitária. 
                    Interprete colunas típicas (Dia da semana, Horário de Início (HH:MM), Horário de Fim (HH:MM),
                    Siglas que representam Disciplina, Sala, Professor).
                    Use a legenda para identificar as siglas e nomes das disciplinas.
                    e retorne no esquema informado."""

#        try:
        disciplinas = parse_with_llm(html, model=OPENAI_MODEL, prompt=prompt, class_=DisciplinasSchedule)
#        except Exception as e:
#            print(f"[yellow]LLM falhou ({e}); usando parser heurístico...[/yellow]")
#            disciplinas = parse_schedule_html(html)
    else:
        disciplinas = parse_schedule_html(html)
    upsert_schedule(g, periodo, curso, instituicao, disciplinas)
    g.close()
    print(f"[green]Linhas de grade processadas e gravadas no grafo.[/green]")

@app.command()
def pull_blog(periodo: str = typer.Option("2025/2", help="Período/Semestre"),
                    curso: str = typer.Option("A", help="Curso"),
                    instituicao: str = typer.Option("Universidade", help="Instituição"),
                    visivel: bool = typer.Option(False, help="Abrir navegador visível")):
    if not (PORTAL_USER and PORTAL_PASS):
        raise typer.Exit("Defina PORTAL_USER/PORTAL_PASS no .env")
    g = Graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    Portal = PortalClient(PORTAL_BASE, PORTAL_USER, PORTAL_PASS, headless=not visivel)
    posts_html = Portal.fetch_blog_posts_html()
    if USE_LLM:
            prompt = """Você recebe HTML soup de um blog universitário com avisos, tarefas, eventos e avaliações. 
                    Interprete informações típicas (Disciplina, Tipo: Aviso, Atividade, Avaliação, data de publicação, prazo).
                    Gere um resumo em poucas palavras.
                    Analise o conteúdo do post e identifique Ações Necessárias para cada postagem 
                    Considere Ação Necessária apenas quando houver prazo mencionado, 
                    implicitamente - próxima aula, próxima semana - ou explicitamente - indicando a data para entrega).
                    Também considere a possibilidade de ações necessárias que não tenham um prazo claro, mas que ainda sejam relevantes, como indicações de leitura.
                    Identifique links do tipo '/Aluno/Post' e retorne no esquema informado."""
            
            posts = []
            for post_html in posts_html:
                blog = parse_with_llm(post_html, model=OPENAI_MODEL, prompt=prompt, class_=BlogPosts)
                time.sleep(0.5)  # Ajuste o tempo conforme necessário para respeitar o TPM
                upsert_blog_posts(g, periodo, curso, instituicao, blog)
                time.sleep(0.5)  # Ajuste o tempo conforme necessário para respeitar o TPM
                posts.append(blog)

            items = posts
    else:
        items = []
#        items = parse_blog_posts_html(html)
    
    #upsert_blog_posts(g,  periodo, curso, instituicao, items)
    g.close()
    #print(f"[green]{len(items)} postagens de blog processadas e gravadas no grafo.[/green]")

@app.command()
def show_schedule(por: str = typer.Option("dia", help="dia|curso")):
    g = Graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    rows = g.list_patterns()
    g.close()
    if por == "dia":
        by = {}
        for r in rows:
            by.setdefault(r["weekday"], []).append(r)
        for wd in sorted(by.keys(), key=lambda x: (x is None, x)):
            print(f"\n[bold]Dia {wd}[/bold]")
            for r in by[wd]:
                print(f"  {r['codigo'] or ''} {r['titulo'] or ''}  {r['start']}-{r['end']}  sala: {r['sala'] or '-'}")
    else:
        by = {}
        for r in rows:
            by.setdefault(r["codigo"], []).append(r)
        for cod in sorted(by.keys()):
            print(f"\n[bold]{cod}[/bold]")
            for r in by[cod]:
                print(f"  {r['weekday']} {r['start']}-{r['end']}  sala: {r['sala'] or '-'}")

@app.command()
def export_ics(saida: str = typer.Option("agenda.ics", help="Arquivo .ics de saída"),
               semanas: int = typer.Option(18, help="Número de semanas para gerar")):
    g = Graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    rows = g.list_patterns()
    g.close()
    path = patterns_to_ics(rows, tzname=LOCAL_TZ, semanas=semanas, path=saida)
    print(f"[green]ICS gerado:[/green] {path}")

def main():
    app()

if __name__ == "__main__":
    main()
