from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Iterable, Literal, Optional

import requests
import typer
from pydantic import BaseModel, Field, HttpUrl, StrictBool, StrictStr, field_validator
from dotenv import load_dotenv
import msal

app = typer.Typer(help="Sync 'todos' with Microsoft To Do via Microsoft Graph (Device Code flow).")

WeekdayName = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
IMPORTANCE = Literal["low", "normal", "high"]
STATUS = Literal["notStarted", "inProgress", "completed", "waitingOnOthers", "deferred"]


class TodoItem(BaseModel):
    external_id: StrictStr = Field(..., description="Stable ID from the source system to guarantee idempotency.")
    title: StrictStr
    notes: Optional[StrictStr] = None
    categories: list[StrictStr] = Field(default_factory=list)
    importance: IMPORTANCE = "normal"
    status: STATUS = "notStarted"
    due_date: Optional[date] = None
    reminded_at: Optional[datetime] = None
    web_url: Optional[HttpUrl] = Field(default=None, description="Optional source URL to appear under Linked Resources.")
    source: list[StrictStr] = Field(default_factory=lambda: ["assistente_de_estudos"])

    @field_validator("reminded_at")
    @classmethod
    def ensure_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AppSettings(BaseModel):
    tenant_id: StrictStr
    client_id: StrictStr
    scopes: list[StrictStr] = Field(default_factory=lambda: ["Tasks.ReadWrite", "offline_access", "openid", "profile"])
    todo_list_name: StrictStr = Field(default="Tasks")
    timezone: StrictStr = Field(default="America/Sao_Paulo")
    dry_run: StrictBool = Field(default=False)

    @classmethod
    def from_env(cls) -> "AppSettings":
        load_dotenv(override=True)
        tenant_id = os.getenv("TENANT_ID") or os.getenv("AZURE_TENANT_ID") or ""
        client_id = os.getenv("CLIENT_ID") or os.getenv("AZURE_CLIENT_ID") or ""
        scopes_str = os.getenv("SCOPES", "")
        scopes = [s.strip() for s in scopes_str.split(",") if s.strip()] if scopes_str else None
        todo_list_name = os.getenv("TODO_LIST_NAME", "Tasks")
        timezone = os.getenv("TIMEZONE", "America/Sao_Paulo")
        dry_run = (os.getenv("DRY_RUN") or "false").lower() in ("1", "true", "yes", "y")
        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            scopes=scopes or ["Tasks.ReadWrite", "offline_access", "openid", "profile"],
            todo_list_name=todo_list_name,
            timezone=timezone,
            dry_run=dry_run,
        )


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._token: Optional[str] = None
        self._app = msal.PublicClientApplication(
            client_id=settings.client_id,
            authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
        )

    def acquire_token(self) -> str:
        if self._token:
            return self._token
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(self.settings.scopes, account=accounts[0])
            if result and "access_token" in result:
                self._token = result["access_token"]
                return self._token
        flow = self._app.initiate_device_flow(scopes=self.settings.scopes)
        if "user_code" not in flow:
            raise RuntimeError("Failed to create device flow. Check your app registration and scopes.")
        print(f"To sign in, visit: {flow['verification_uri']} and enter code: {flow['user_code']}")
        result = self._app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(f"Authentication failed: {result.get('error_description')}")
        self._token = result["access_token"]
        return self._token

    def _headers(self) -> dict:
        token = self.acquire_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def get_list_id(self, list_name: str) -> Optional[str]:
        url = f"{GRAPH_ROOT}/me/todo/lists"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("value", []):
            if item.get("displayName") == list_name:
                return item.get("id")
        return None

    def create_list(self, list_name: str) -> str:
        url = f"{GRAPH_ROOT}/me/todo/lists"
        payload = {"displayName": list_name}
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]

    def ensure_list(self, list_name: str) -> str:
        list_id = self.get_list_id(list_name)
        if list_id:
            return list_id
        return self.create_list(list_name)

    def find_task_by_external_id(self, list_id: str, external_id: str) -> Optional[dict]:
        url = f"{GRAPH_ROOT}/me/todo/lists/{list_id}/tasks?$top=50"
        while url:
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for task in data.get("value", []):
                task_id = task.get("id")
                if not task_id:
                    continue
                lr_url = f"{GRAPH_ROOT}/me/todo/lists/{list_id}/tasks/{task_id}/linkedResources"
                lr = requests.get(lr_url, headers=self._headers(), timeout=30).json()
                for r in lr.get("value", []):
                    if r.get("externalId") == external_id:
                        return task
            url = data.get("@odata.nextLink")
        return None

    def upsert_task(self, list_id: str, item: 'TodoItem', timezone_str: str) -> dict:
        payload: dict = {
            "title": item.title,
            "importance": item.importance,
            "status": item.status,
            "body": {"content": item.notes or "", "contentType": "text"},
            "categories": item.categories or [],
        }
        if item.due_date:
            payload["dueDateTime"] = {
                "dateTime": datetime(item.due_date.year, item.due_date.month, item.due_date.day, 23, 59, 0).isoformat(),
                "timeZone": timezone_str,
            }
        if item.reminded_at:
            payload["reminderDateTime"] = {
                "dateTime": item.reminded_at.isoformat(),
                "timeZone": timezone_str,
            }

        existing = self.find_task_by_external_id(list_id, item.external_id)
        if existing:
            task_id = existing["id"]
            if not AppSettings.from_env().dry_run:
                url = f"{GRAPH_ROOT}/me/todo/lists/{list_id}/tasks/{task_id}"
                resp = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
                resp.raise_for_status()
                updated = resp.json()
                self._ensure_linked_resource(list_id, updated["id"], item)
                return updated
            else:
                return {"id": task_id, "title": item.title, "dryRun": True, "action": "update"}
        else:
            if not AppSettings.from_env().dry_run:
                url = f"{GRAPH_ROOT}/me/todo/lists/{list_id}/tasks"
                resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
                resp.raise_for_status()
                created = resp.json()
                self._ensure_linked_resource(list_id, created["id"], item)
                return created
            else:
                return {"id": "new", "title": item.title, "dryRun": True, "action": "create"}

    def _ensure_linked_resource(self, list_id: str, task_id: str, item: 'TodoItem') -> None:
        url = f"{GRAPH_ROOT}/me/todo/lists/{list_id}/tasks/{task_id}/linkedResources"
        payload = {
            "applicationName": "Assistente de Estudos",
            "externalId": item.external_id,
            "webUrl": str(item.web_url) if item.web_url else None,
            "displayName": item.source[0] if item.source else "source",
        }
        existing = requests.get(url, headers=self._headers(), timeout=30).json().get("value", [])
        found = next((r for r in existing if r.get("externalId") == item.external_id), None)
        if found:
            return
        requests.post(url, headers=self._headers(), json=payload, timeout=30).raise_for_status()


def sample_generate_tasks() -> list[TodoItem]:
    today = date.today()
    items = [
        TodoItem(
            external_id=f"demo-{today.isoformat()}-1",
            title="Revisar anotações de Psicologia Analítica",
            notes="Dedicar 30 minutos à revisão do capítulo sobre arquétipos.",
            categories=["estudos", "jung"],
            importance="normal",
            status="notStarted",
            due_date=today + timedelta(days=1),
        ),
        TodoItem(
            external_id=f"demo-{today.isoformat()}-2",
            title="Preparar roteiro do vídeo 'A Alma no Laboratório'",
            notes="Rascunhar tópicos principais e separar referências.",
            categories=["vídeo", "roteiro"],
            importance="high",
            status="inProgress",
            due_date=today + timedelta(days=3),
        ),
    ]
    return items


@app.command("generate")
def generate(
    output: Annotated[Optional[str],  typer.Option("--out", "-o",help="Path to write generated tasks JSON")] = "tasks.generated.json"
):
    items = sample_generate_tasks()
    data = [json.loads(i.model_dump_json()) for i in items]
    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(data)} task(s) to {output}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


@app.command("push")
def push(
    input_path: Annotated[str, typer.Argument(help="JSON file with a list[TodoItem].")],
    list_name: Annotated[Optional[str], typer.Option("--list-name", "-l", help="Target To Do list name")] = None,
):
    settings = AppSettings.from_env()
    if list_name:
        settings.todo_list_name = list_name
    client = GraphClient(settings)

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    items = [TodoItem.model_validate(obj) for obj in raw]
    list_id = client.ensure_list(settings.todo_list_name)

    results = []
    for item in items:
        res = client.upsert_task(list_id, item, settings.timezone)
        results.append(res)

    print(json.dumps(results, ensure_ascii=False, indent=2))


@app.command("sync")
def sync(
    output: Annotated[Optional[str], typer.Option("--out", "-o", help="Where to save the generated JSON before push")] = "tasks.generated.json",
    list_name: Annotated[Optional[str], typer.Option("--list-name", "-l", help="Target To Do list name")] = None,
):
    items = sample_generate_tasks()
    data = [json.loads(i.model_dump_json()) for i in items]
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[1/2] Generated {len(data)} tasks → {output}")

    settings = AppSettings.from_env()
    if list_name:
        settings.todo_list_name = list_name
    client = GraphClient(settings)
    list_id = client.ensure_list(settings.todo_list_name)

    results = []
    for obj in data:
        item = TodoItem.model_validate(obj)
        res = client.upsert_task(list_id, item, settings.timezone)
        results.append(res)
    print("[2/2] Push complete.")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
