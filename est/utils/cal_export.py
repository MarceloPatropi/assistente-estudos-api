from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz
from fastapi import FastAPI
from contextlib import asynccontextmanager

def patterns_to_ics(patterns, tzname: str, semanas: int=18, path: str="agenda.ics"):
    tz = pytz.timezone(tzname)
    today = datetime.now(tz).date()
    base_monday = today + timedelta(days=(0 - today.weekday()) % 7) + timedelta(days=7)

    cal = Calendar()
    for p in patterns:
        wd = p["weekday"]
        if wd is None or not p.get("start") or not p.get("end"):
            continue
        h1, m1 = map(int, p["start"].split(":"))
        h2, m2 = map(int, p["end"].split(":"))
        for w in range(semanas):
            day = base_monday + timedelta(days=wd, weeks=w)
            start_dt = tz.localize(datetime(day.year, day.month, day.day, h1, m1))
            end_dt   = tz.localize(datetime(day.year, day.month, day.day, h2, m2))
            ev = Event()
            ev.name = f"{p.get('codigo') or ''} {p.get('titulo') or ''}".strip() or "Aula"
            ev.location = p.get("sala") or "Campus"
            ev.begin = start_dt
            ev.end = end_dt
            cal.events.add(ev)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(cal)
    return path

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicialização (antes era no "startup")
    # Exemplo: await inicializar_bot()
    yield
    # Código de finalização (antes era no "shutdown")
    # Exemplo: await finalizar_bot()

app = FastAPI(lifespan=lifespan)
