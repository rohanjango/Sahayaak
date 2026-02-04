from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import PyPDF2
from PIL import Image
import io
import base64


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class FormSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    form_link: Optional[str] = None
    file_name: Optional[str] = None
    transcription: str
    extracted_text: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FormSubmissionCreate(BaseModel):
    form_link: Optional[str] = None
    file_name: Optional[str] = None
    transcription: str
    extracted_text: Optional[str] = None


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Voice Form Filling API"}

@api_router.post("/upload-form")
async def upload_form(file: UploadFile = File(...)):
    """Upload and process form file (PDF or image)"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        contents = await file.read()
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        file_extension = file.filename.split('.')[-1].lower()
        extracted_text = ""
        
        if file_extension == 'pdf':
            try:
                # Extract text from PDF
                pdf_file = io.BytesIO(contents)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                if len(pdf_reader.pages) == 0:
                    extracted_text = "PDF file appears to be empty or corrupted"
                else:
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                    
                    if not extracted_text.strip():
                        extracted_text = "PDF processed successfully but no text could be extracted (might be image-based PDF)"
            
            except Exception as pdf_error:
                logging.error(f"PDF processing error: {str(pdf_error)}")
                extracted_text = f"PDF uploaded but text extraction failed: {str(pdf_error)}"
        
        elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            try:
                # For images, validate and return basic info
                image = Image.open(io.BytesIO(contents))
                extracted_text = f"Image uploaded successfully: Format={image.format}, Size={image.size[0]}x{image.size[1]}px, Mode={image.mode}"
            except Exception as img_error:
                logging.error(f"Image processing error: {str(img_error)}")
                extracted_text = f"Image uploaded but processing failed: {str(img_error)}"
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: .{file_extension}. Supported formats: PDF, PNG, JPG, JPEG")
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "extracted_text": extracted_text,
            "message": "File processed successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.post("/save-submission", response_model=FormSubmission)
async def save_submission(submission: FormSubmissionCreate):
    """Save form submission to database"""
    try:
        submission_obj = FormSubmission(**submission.model_dump())
        
        doc = submission_obj.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        await db.form_submissions.insert_one(doc)
        
        return submission_obj
    except Exception as e:
        logging.error(f"Error saving submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving submission: {str(e)}")

@api_router.get("/submissions", response_model=List[FormSubmission])
async def get_submissions():
    """Get all form submissions"""
    try:
        submissions = await db.form_submissions.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
        
        for submission in submissions:
            if isinstance(submission['timestamp'], str):
                submission['timestamp'] = datetime.fromisoformat(submission['timestamp'])
        
        return submissions
    except Exception as e:
        logging.error(f"Error fetching submissions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching submissions: {str(e)}")

@api_router.delete("/submissions/{submission_id}")
async def delete_submission(submission_id: str):
    """Delete a specific submission"""
    try:
        result = await db.form_submissions.delete_one({"id": submission_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        return {"success": True, "message": "Submission deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting submission: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
