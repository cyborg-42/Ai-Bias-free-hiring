import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import the core logic from your local parser
from resume_parser import parse_and_score_resume

# --- Configuration ---
app = FastAPI(title="Inclusive Talent Mapper API")
UPLOAD_FOLDER = "temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. Setup Jinja2 Templates
templates = Jinja2Templates(directory="templates")

# 2. Mount the Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Routes ---

# 1. Root Route (GET: Serves the HTML Frontend)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main page of the application.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": None, "role_name": None} # Pass role_name as None initially
    )


# 2. Analysis Route (POST: Handles Upload and Scoring)
@app.post("/score", name="upload_file_and_score")
async def upload_file_and_score(
    request: Request,
    file: UploadFile = File(...),
    role_name: str = Form(...)  # Correctly receive the role_name from the form
):
    """
    Handles the file upload, calls the analysis function, and returns the results.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save File Temporarily
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        # Ensure the uploaded file object is closed
        await file.close()

    # Core Processing (Calling your local, rule-based logic)
    analysis_result = {}
    try:
        analysis_result = parse_and_score_resume(filepath, role_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"FATAL PROCESSING ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during analysis: {e}")
    finally:
        # Cleanup: always remove the temporary file
        if os.path.exists(filepath):
            os.remove(filepath)

    # **THE FIX IS HERE:**
    # Return the results, now including the 'role_name' for the template.
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": analysis_result,
            "role_name": role_name  # <-- This line was added
        }
    )


# 3. Server Start Command
if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

