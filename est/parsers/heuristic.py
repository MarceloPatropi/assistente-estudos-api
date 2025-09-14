from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

WEEKDAYS = {
    "segunda":0, "segunda-feira":0, "seg":0,
    "terça":1, "terca":1, "terça-feira":1, "ter":1,
    "quarta":2, "quarta-feira":2, "qua":2,
    "quinta":3, "quinta-feira":3, "qui":3,
    "sexta":4, "sexta-feira":4, "sex":4,
    "sábado":5, "sabado":5, "sáb":5, "sab":5,
    "domingo":6, "dom":6,
}
HORA_RE = re.compile(r"(\d{1,2})[:h](\d{2})", re.I)

def parse_schedule_html(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for tbl in soup.find_all("table"):
        headers = " ".join(th.get_text(" ", strip=True).lower() for th in tbl.find_all("th"))
        if any(k in headers for k in ("disciplina","hor","início","inicio","sala")):
            table = tbl
            break
    rows = []
    if not table:
        return rows
    for tr in table.find_all("tr")[1:]:
        cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td","th"])]
        if len(cols) < 2: continue
        txt = " | ".join(cols).lower()
        wd = None
        for k,v in WEEKDAYS.items():
            if k in txt: wd = v; break
        horas = re.findall(HORA_RE, txt)
        if len(horas)>=2:
            start = f"{int(horas[0][0]):02d}:{int(horas[0][1]):02d}"
            end   = f"{int(horas[1][0]):02d}:{int(horas[1][1]):02d}"
        elif len(horas)==1:
            start = f"{int(horas[0][0]):02d}:{int(horas[0][1]):02d}"
            end   = None
        else:
            start, end = None, None
        disc = next((c for c in cols if 10 < len(c) < 80 and not any(ch.isdigit() for ch in c)), "Disciplina")
        sala = next((c for c in cols if "sala" in c.lower()), None)
        prof = next((c for c in cols if "prof" in c.lower()), None)
        rows.append({
            "weekday": wd, "start": start, "end": end,
            "disciplina": disc, "sala": sala, "professor": prof, "source": cols
        })
    return rows
