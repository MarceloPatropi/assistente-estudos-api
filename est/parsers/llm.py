import os, re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from openai import OpenAI
from pydantic import BaseModel
import json
from est.features.openai_cache import get_cached_response, set_cached_response

WEEKDAYS = {
    "segunda":0, "segunda-feira":0, "seg":0,
    "terça":1, "terca":1, "terça-feira":1, "ter":1,
    "quarta":2, "quarta-feira":2, "qua":2,
    "quinta":3, "quinta-feira":3, "qui":3,
    "sexta":4, "sexta-feira":4, "sex":4,
    "sábado":5, "sabado":5, "sáb":5, "sab":5,
    "domingo":6, "dom":6,
}

def _extract_tables(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables: return ""
    cands = []
    for tbl in tables:
        head = " ".join(th.get_text(" ", strip=True).lower() for th in tbl.find_all("th"))
        body = " ".join(td.get_text(" ", strip=True).lower() for td in tbl.find_all("td")[:30])
        score = sum(k in head or k in body for k in ("disciplina","hor","sala","prof"))
        if score >= 2: cands.append(tbl)
    if not cands: cands = tables[:1]
    return "\n".join(str(t) for t in cands)

def parse_with_llm(raw_html: str, model: str = "gpt-5-nano", prompt: str = "", class_: BaseModel = None) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Defina OPENAI_API_KEY no .env")
    client = OpenAI(api_key=api_key)
    model = model or os.getenv("OPENAI_MODEL", "gpt-5-nano")
    soup = BeautifulSoup(raw_html, "html.parser")
#    elements_html = _extract_relevant_elements(raw_html)
#    if not elements_html.strip(): return []

    system = prompt or ("Você é um assistente que extrai informações estruturadas de HTML soup." )
    user = "HTML Soup:\\n" + soup.prettify()[:150000]
    response_class = class_ or BaseModel

    print("Enviando para LLM...")

    resp = client.responses.parse(
        model=model,
        input=[{"role":"system","content":system},{"role":"user","content":user}],
        text_format=response_class,
    )
    data = resp.output_text
    if class_ and not isinstance(data, class_):
        try:
            data = class_.model_validate(json.loads(data))
        except Exception:
            try:
                data = class_(**json.loads(data))
            except Exception:
                pass
    try:
        data = json.loads(data)
    except Exception:
        pass    

    return data

def call_openai_api(params: dict):
    # Remover ou substituir 'class_' por string antes de usar no cache
    cache_params = dict(params)
    if "class_" in cache_params:
        cache_params["class_"] = str(cache_params["class_"].__name__)
    cached = get_cached_response(cache_params)
    if cached:
        return cached
    response = parse_with_llm(**params)
    set_cached_response(cache_params, response)
    return response
