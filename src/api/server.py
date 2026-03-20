import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
from main import run_pipeline
from src.core.logger import logger
from src.core.config import INPUTS_DIR, OUTPUTS_DIR
import traceback

app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max

task_status = {
    "status": "idle",
    "stage": "",
    "message": "",
    "progress": 0,
    "eta_seconds": None,
    "output_file": None
}

cancel_flag = False

def process_video_background(video_source: str):
    global task_status, cancel_flag

    def status_updater(progress, stage, message, eta_seconds):
        if cancel_flag:
            raise Exception("Task cancelled by user")
        task_status["progress"] = progress
        task_status["stage"] = stage
        task_status["message"] = message
        task_status["eta_seconds"] = round(eta_seconds) if eta_seconds is not None else None

    try:
        final_video_path = run_pipeline(video_source, status_updater=status_updater)
        task_status["status"] = "completed"
        task_status["progress"] = 100
        task_status["message"] = "Pipeline finished successfully!"
        task_status["output_file"] = os.path.basename(final_video_path)
    except Exception as e:
        if cancel_flag:
            task_status["status"] = "cancelled"
            task_status["message"] = "Task cancelled by user"
        else:
            task_status["status"] = "error"
            task_status["message"] = str(e)
        logger.error(f"Background task failed: {e}")
        logger.debug(traceback.format_exc())

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dub", methods=["POST"])
def dub_video():
    global task_status, cancel_flag
    
    video_path = None
    
    if 'file' in request.files:
        file = request.files['file']
        if file.filename:
            video_path = os.path.join(INPUTS_DIR, file.filename)
            os.makedirs(INPUTS_DIR, exist_ok=True)
            file.save(video_path)
    
    url = request.form.get("url") or (request.json.get("url") if request.is_json else None)
    
    if not video_path and not url:
        return jsonify({"error": "No video file or URL provided"}), 400
        
    if task_status["status"] == "processing":
        return jsonify({"error": "A job is already running! Please wait for it to finish."}), 429
    
    cancel_flag = False
    task_status = {
        "status": "processing",
        "stage": "Initializing",
        "message": "Initializing...",
        "progress": 0,
        "eta_seconds": None,
        "output_file": None
    }
    
    video_source = video_path if video_path else url
    t = threading.Thread(target=process_video_background, args=(video_source,))
    t.daemon = True
    t.start()
    
    return jsonify({"message": "Job started", "status": "processing"})

@app.route("/api/stop", methods=["POST"])
def stop_task():
    global task_status, cancel_flag
    if task_status["status"] != "processing":
        return jsonify({"error": "No task running"}), 400
    
    cancel_flag = True
    task_status["message"] = "Stopping..."

    return jsonify({"message": "Stopping task..."})

@app.route("/api/status", methods=["GET"])
def get_status():
    global task_status
    return jsonify(task_status.copy())

@app.route("/outputs/<path:filename>")
def get_output(filename):
    return send_from_directory(OUTPUTS_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
