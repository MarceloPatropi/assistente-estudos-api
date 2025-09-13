import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler
import asyncio

# importa sua lógica já existente
from cli import pull_schedule
from sync_todo import sync as sync_todo

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://seu-dominio.com/telegram")

app = FastAPI()
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Exemplo: comando /agenda
async def agenda(update: Update, context):
    try:
        pull_schedule(periodo="2025/2", curso="A", instituicao="Universidade")
        await update.message.reply_text("✅ Agenda sincronizada no Neo4j!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Erro ao puxar agenda: {e}")

# Exemplo: comando /todo
async def todo(update: Update, context):
    try:
        sync_todo()
        await update.message.reply_text("✅ Tarefas sincronizadas com Microsoft To Do!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Erro ao sincronizar tarefas: {e}")

# registra os comandos
telegram_app.add_handler(CommandHandler("agenda", agenda))
telegram_app.add_handler(CommandHandler("todo", todo))

@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await telegram_app.bot.set_webhook(WEBHOOK_URL)