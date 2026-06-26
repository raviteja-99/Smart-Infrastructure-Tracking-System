from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3
import cv2
import numpy as np
import os
import uuid
import random
import json
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
import io

from database import init_db, DB_NAME

app = FastAPI(title="Smart Infrastructure Tracking API")

init_db()
app.mount("/static", StaticFiles(directory="static"), name="static")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserAuth(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(user: UserAuth):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        hashed_password = pwd_context.hash(user.password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user.username, hashed_password))
        conn.commit()
        return {"message": "User registered successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (user.username,))
    record = c.fetchone()
    conn.close()
    
    if not record or not pwd_context.verify(user.password, record[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "username": user.username}

@app.post("/upload/")
async def upload_image(
    file: UploadFile = File(...), 
    structure_type: str = Form("Other"),
    lat: float = Form(None),
    lon: float = Form(None)
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Simulate AI Damage Detection
    height, width, _ = img.shape
    start_point = (int(width * 0.2), int(height * 0.2))
    end_point = (int(width * 0.4), int(height * 0.4))
    color = (0, 0, 255) 
    thickness = 3
    img_annotated = cv2.rectangle(img, start_point, end_point, color, thickness)
    cv2.putText(img_annotated, 'Crack Detected (0.89)', (start_point[0], start_point[1]-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    uid = str(uuid.uuid4())
    filename = f"{uid}.jpg"
    filepath = os.path.join("static", filename)
    cv2.imwrite(filepath, img_annotated)
    
    percent_complete = round(random.uniform(40.0, 95.0), 2)
    
    # Define mock damages for this upload
    damages = [
        {"label": "Structural Crack", "score": 0.89},
        {"label": "Surface Corrosion", "score": 0.65}
    ]
    
    # Save to database for PDF retrieval
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO uploads (uid, filename, structure_type, percent_complete, damages, image_path) VALUES (?, ?, ?, ?, ?, ?)",
              (uid, file.filename, structure_type, percent_complete, json.dumps(damages), filepath))
    conn.commit()
    conn.close()
    
    return {
        "upload_id": uid,
        "filename": file.filename,
        "structure_type": structure_type,
        "percent_complete": percent_complete,
        "annotated": f"/static/{filename}",
        "damages": damages
    }

@app.get("/history/summary")
def get_summary():
    return {
        "average_percent_complete": 67.23,
        "months_remaining_estimate": 6.6,
        "accuracy_estimate": "92.4%"
    }

@app.get("/pdf/{uid}")
def generate_pdf(uid: str):
    # Fetch upload data from DB
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT filename, structure_type, percent_complete, damages, image_path FROM uploads WHERE uid = ?", (uid,))
    record = c.fetchone()
    conn.close()

    if not record:
        raise HTTPException(status_code=404, detail="Upload ID not found. Ensure the image was uploaded.")

    filename, structure_type, percent_complete, damages_json, image_path = record
    damages = json.loads(damages_json)

    # 1. Generate Graph using Matplotlib
    plt.figure(figsize=(5, 4))
    labels = [d['label'] for d in damages]
    scores = [d['score'] * 100 for d in damages]
    plt.bar(labels, scores, color=['#e74c3c', '#e67e22', '#f1c40f'][:len(labels)])
    plt.ylim(0, 100)
    plt.ylabel('Confidence Score (%)')
    plt.title('Detected Damage Confidence')
    plt.tight_layout()
    graph_path = os.path.join("static", f"{uid}_graph.png")
    plt.savefig(graph_path)
    plt.close()

    # 2. Generate PDF using ReportLab
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    
    # Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, 800, "Smart Infrastructure Tracking Report")
    
    # Details
    p.setFont("Helvetica", 12)
    p.drawString(50, 770, f"Report ID: {uid}")
    p.drawString(50, 750, f"Original File: {filename}")
    p.drawString(50, 730, f"Structure Type: {structure_type}")
    p.drawString(50, 710, f"Completion Estimate: {percent_complete}%")
    
    # Damage Descriptions
    p.setFont("Helvetica-Bold", 12)
    y_text = 680
    p.drawString(50, y_text, "Identified Damages & Anomalies:")
    p.setFont("Helvetica", 12)
    y_text -= 25
    for d in damages:
        p.drawString(70, y_text, f"• {d['label']}: Detected with {d['score']*100:.1f}% AI confidence.")
        y_text -= 20
        
    y_text -= 20 
    
    # Images (Annotated Image & Graph)
    p.setFont("Helvetica-Bold", 12)
    if os.path.exists(image_path):
        p.drawString(50, y_text, "Site Image (Annotated):")
        # Draw Image (x, y, width, height)
        p.drawImage(image_path, 50, y_text - 220, width=240, height=200, preserveAspectRatio=True)
        
    if os.path.exists(graph_path):
        p.drawString(320, y_text, "Damage Confidence Graph:")
        p.drawImage(graph_path, 320, y_text - 220, width=240, height=200, preserveAspectRatio=True)

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 50, "Generated automatically by AI Smart Infrastructure Tracker.")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf")