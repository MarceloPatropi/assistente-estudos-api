from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Assistente de Estudos API", version="1.0.0")

# Pydantic models
class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskSync(BaseModel):
    tasks: List[Task]

class ScheduleResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

class UploadResponse(BaseModel):
    status: str
    filename: str
    message: str

# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Assistente de Estudos API"}

# Todo sync endpoint - POST JSON tasks
@app.post("/todo/sync", response_model=dict)
async def sync_tasks(task_sync: TaskSync):
    """Sync tasks - receives a list of tasks in JSON format"""
    try:
        # Process the tasks (placeholder logic)
        processed_tasks = []
        for task in task_sync.tasks:
            # Add ID if not present
            if task.id is None:
                task.id = len(processed_tasks) + 1
            processed_tasks.append(task.dict())
        
        return {
            "status": "success",
            "message": f"Synchronized {len(processed_tasks)} tasks",
            "tasks": processed_tasks
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error synchronizing tasks: {str(e)}")

# Portal schedule pull endpoint - POST form data
@app.post("/portal/pull_schedule", response_model=ScheduleResponse)
async def pull_schedule(
    periodo: str = Form(..., description="Academic period"),
    curso: str = Form(..., description="Course name"),
    instituicao: str = Form(..., description="Institution name")
):
    """Pull schedule from portal - receives form data with periodo, curso, instituicao"""
    try:
        # Placeholder logic for pulling schedule
        schedule_data = {
            "periodo": periodo,
            "curso": curso,
            "instituicao": instituicao,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        return ScheduleResponse(
            status="success",
            message=f"Schedule pulled for {curso} at {instituicao} for period {periodo}",
            data=schedule_data
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error pulling schedule: {str(e)}")

# File upload endpoint
@app.post("/ingest/upload", response_model=UploadResponse)
async def upload_file(arquivo: UploadFile = File(...)):
    """Upload file for ingestion"""
    try:
        # Validate file
        if not arquivo.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content (placeholder - in real implementation, you'd save/process it)
        content = await arquivo.read()
        file_size = len(content)
        
        # Placeholder logic for file processing
        return UploadResponse(
            status="success",
            filename=arquivo.filename,
            message=f"File '{arquivo.filename}' uploaded successfully ({file_size} bytes)"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error uploading file: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Assistente de Estudos API",
        "version": "1.0.0",
        "endpoints": [
            "GET /healthz - Health check",
            "POST /todo/sync - Sync tasks (JSON)",
            "POST /portal/pull_schedule - Pull schedule (form data)",
            "POST /ingest/upload - Upload file"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)