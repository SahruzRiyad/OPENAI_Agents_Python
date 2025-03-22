from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from task_2 import create_new_task, get_status, collection, run_task
import asyncio
import uvicorn

app = FastAPI()

# Pydantic model for request validation
class TaskRequest(BaseModel):
    query: str

# Create task endpoint
@app.post("/task", status_code=status.HTTP_200_OK)
async def task_create(task_request: TaskRequest):
    query = task_request.query

    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query is required.")

    # Create a new task
    task_id = create_new_task(query)

    # Scheduling the background task
    asyncio.create_task(run_task(task_id))

    response = {
        'success': True,
        'query': query,
        'task_id': task_id,
        'status': get_status(task_id)
    }

    return response

# Check task status endpoint
@app.get("/task/{task_id}", status_code=status.HTTP_200_OK)
async def check_task_status(task_id: str):
    task_status = get_status(task_id)

    if not task_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    
    elif task_status != "Done":
        return {
            'status': task_status
        }
    
    else:
        result = collection.find_one({"task_id": task_id})

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task result not found in database.")

        response = {
            'task_id': task_id,
            'status': task_status,
            'query': result['query'],
            'scraped_url': result['scraped_url'],
            'tutorial': result['tutorial']
        }

        return response

# Runing FastAPI app
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)