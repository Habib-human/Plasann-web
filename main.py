from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import run_pipeline  # Import the pipeline script

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- Allows all origins (change to ["http://127.0.0.1:8001"] for security)
    allow_credentials=True,
    allow_methods=["*"],  # <-- Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # <-- Allows all headers
)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "FastAPI is running!"}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """ Accepts file upload, detects file type, and runs the plasmid annotation pipeline """
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Run the pipeline and get result filenames
    try:
        output_png, output_csv, output_gbk = run_pipeline.run_pipeline(file_path, RESULT_FOLDER)
    except Exception as e:
        return {"error": str(e)}

    # Extract plasmid name (subfolder name) from the file
    plasmid_name = os.path.basename(file.filename).split('.')[0]
    plasmid_folder = os.path.join(RESULT_FOLDER, plasmid_name)

    # **Update filenames based on actual output format**
    png_filename = f"Annotated_Map_for_{plasmid_name}.png"
    csv_filename = f"Annotation_table_for_{plasmid_name}.csv"
    gbk_filename = f"Annotation_gbk_file_for_{plasmid_name}.gbk"

    return {
        "message": "Processing completed",
        "png_url": f"/results/{plasmid_name}/{png_filename}",
        "csv_url": f"/results/{plasmid_name}/{csv_filename}",
        "gbk_url": f"/results/{plasmid_name}/{gbk_filename}"
    }

@app.get("/results/{plasmid}/{filename}")
async def get_result_file(plasmid: str, filename: str):
    """ Serves the result files from subfolders """
    file_path = os.path.join(RESULT_FOLDER, plasmid, filename)

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    return FileResponse(file_path)
