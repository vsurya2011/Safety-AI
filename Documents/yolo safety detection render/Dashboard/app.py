import os
import io
import csv
import cv2
import random
import tempfile
import threading
import datetime
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')  # For server image generation
import matplotlib.pyplot as plt

from collections import deque
from ultralytics import YOLO
from flask import (
    Flask, render_template, Response, request, redirect,
    url_for, make_response, session
)

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
fps_value = 0.0
fps_history = []
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-for-yolo'
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

STATIC_GEN_DIR = os.path.join(app.static_folder, 'generated')
os.makedirs(STATIC_GEN_DIR, exist_ok=True)

# Your actual violation classes
VIOLATION_CLASSES = {"NO-Hardhat", "NO-Safety Vest", "NO-Mask"}

# -------------------------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------------------------

data_lock = threading.Lock()

violations = pd.DataFrame(
    columns=["Time of Violation", "Saved as Snapshot.No", "Type of Violation"]
)

snapshots = deque(maxlen=50)   # store latest 50 snapshots
processing = False
video_path = None
snapshot_counter = 0

# -------------------------------------------------------------------
# LOAD YOLO MODEL
# -------------------------------------------------------------------

try:
    model = YOLO("best.pt")
    print("Loaded model with classes:", model.names)
except Exception as e:
    print("Error loading 'best.pt':", e)
    model = None

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------

def save_snapshot(img_bgr, snapshot_name):
    """ Save BGR -> PNG into static/generated folder """
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    filename = f"{snapshot_name}.png"
    full_path = os.path.join(STATIC_GEN_DIR, filename)
    plt.imsave(full_path, rgb)
    return f"generated/{filename}"
    
def generate_bar_plot(df):
    if df.empty:
        return None

    counts = df["Type of Violation"].value_counts()
    if counts.empty:
        return None

    fig, ax = plt.subplots(figsize=(6,4))
    ax.bar(counts.index, counts.values, color="#4A4AFF")
    ax.set_title("Violations by Type")
    ax.set_ylabel("Count")

    plt.xticks(rotation=45, ha="right")
    fig.patch.set_facecolor("#0A0A0A")
    ax.set_facecolor("#0A0A0A")
    ax.tick_params(colors="white")

    for spine in ax.spines.values():
        spine.set_color("#555")

    bar_path = os.path.join(STATIC_GEN_DIR, "bar_plot.png")
    fig.savefig(bar_path, bbox_inches="tight", facecolor="#0A0A0A")
    plt.close(fig)

    return "generated/bar_plot.png"

def generate_line_plot(df):
    if len(df) < 2:
        return None

    df_copy = df.copy()
    df_copy["Time of Violation"] = pd.to_datetime(df_copy["Time of Violation"])
    ts = df_copy.set_index("Time of Violation").resample("T").size()

    if ts.empty:
        return None

    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(ts.index, ts.values, marker="o", color="#00FF00")
    ax.set_title("Violations Over Time (per minute)")
    ax.set_ylabel("Count")

    plt.xticks(rotation=45, ha="right")
    fig.patch.set_facecolor("#0A0A0A")
    ax.set_facecolor("#0A0A0A")
    ax.tick_params(colors="white")

    for spine in ax.spines.values():
        spine.set_color("#555")

    line_path = os.path.join(STATIC_GEN_DIR, "line_plot.png")
    fig.savefig(line_path, bbox_inches="tight", facecolor="#0A0A0A")
    plt.close(fig)

    return "generated/line_plot.png"

# -------------------------------------------------------------------
# YOLO PROCESSING — ONLY LOG REAL VIOLATIONS
# -------------------------------------------------------------------

def real_yolo_process_frame(frame, model):
    global snapshot_counter, snapshots, violations

    if model is None:
        return frame

    try:
        results = model.predict(frame, verbose=False)
    except Exception as e:
        print("YOLO predict error:", e)
        return frame

    try:
        processed_frame = results[0].plot()
    except:
        processed_frame = frame

    violation_found = None

    for r in results:
        for box in r.boxes:
            try:
                class_id = int(box.cls[0])
                label = model.names[class_id]
            except:
                continue

            print("Detected:", label)

            if label in VIOLATION_CLASSES:
                print("🚨 VIOLATION:", label)

                violation_found = {
                    "time": datetime.datetime.now(),
                    "type": label,
                    "snapshot": frame.copy()
                }
                break
        if violation_found:
            break

    # Log violation
    if violation_found:
        with data_lock:
            snapshot_counter += 1
            snap_name = f"snapshot_{snapshot_counter:04d}"

            # save file to static/generated
            snap_rel_path = save_snapshot(violation_found["snapshot"], snap_name)

            new_row = {
                "Time of Violation": violation_found["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "Saved as Snapshot.No": snap_name,
                "Type of Violation": violation_found["type"]
            }

            violations.loc[len(violations)] = new_row

            snapshots.append({
                "name": snap_name,
                "path": snap_rel_path
            })

    return processed_frame

# -------------------------------------------------------------------
# VIDEO STREAMING
# -------------------------------------------------------------------

def generate_frames():
    global processing, video_path, fps_value, fps_history

    import time

    if not video_path or not os.path.exists(video_path):
        return

    cap = cv2.VideoCapture(video_path)
    prev_time = time.time()

    while cap.isOpened():
        with data_lock:
            if not processing:
                break

        ret, frame = cap.read()
        if not ret:
            break

        # ---- FPS CALCULATION ----
        curr_time = time.time()
        dt = curr_time - prev_time
        prev_time = curr_time

        if dt > 0:
            fps_value = round(1.0 / dt, 2)
            fps_history.append(fps_value)
            if len(fps_history) > 60:
                fps_history.pop(0)
        # --------------------------

        processed = real_yolo_process_frame(frame, model)

        flag, buffer = cv2.imencode(".jpg", processed)
        if not flag:
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            buffer.tobytes() +
            b'\r\n'
        )

    cap.release()

    with data_lock:
        processing = False


# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------

@app.route("/")
def start_page():
    if "background" not in session:
        session["background"] = random.choice(["red.html", "colors.html"])
    return render_template("start.html")

@app.route("/page/<page_name>")
def show_page(page_name):
    template = f"{page_name}.html"
    if not os.path.exists(os.path.join(app.template_folder, template)):
        return "Page not found", 404

    ctx = {
        "current_page": page_name,
        "video_path": video_path,
        "processing": processing
    }

    if page_name == "statistics":
        with data_lock:
            ctx["violations_data"] = violations.to_dict(orient="records")

            paths = {}
            b = generate_bar_plot(violations)
            if b: paths["bar"] = b

            l = generate_line_plot(violations)
            if l: paths["line"] = l

            ctx["plot_paths"] = paths

    if page_name == "snapshots":
        with data_lock:
            ctx["snapshot_files"] = list(reversed(snapshots))

    return render_template(template, **ctx)

@app.route("/upload_video", methods=["POST"])
def upload_video():
    global video_path, processing

    file = request.files.get("video_file")
    if not file or file.filename == "":
        return redirect(url_for("show_page", page_name="view"))

    with data_lock:
        processing = False

    filename = "uploaded_video.mp4"
    new_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(new_path)

    with data_lock:
        video_path = new_path

    return redirect(url_for("show_page", page_name="view"))

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/start_processing")
def start_processing():
    global processing
    with data_lock:
        if video_path and os.path.exists(video_path):
            processing = True
    return redirect(url_for("show_page", page_name="view"))

@app.route("/stop_processing")
def stop_processing():
    global processing
    with data_lock:
        processing = False
    return redirect(url_for("show_page", page_name="view"))

@app.route("/download_csv")
def download_csv():
    with data_lock:
        df = violations.copy()

    if df.empty:
        return "No violations yet", 404

    csv_data = df.to_csv(index=False)
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=violations.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/set_background/<bg_name>")
def set_background(bg_name):
    if bg_name in ["red", "colors"]:
        session["background"] = f"{bg_name}.html"
    return redirect(url_for("start_page"))

@app.route("/get_fps")
def get_fps():
    global fps_value, fps_history
    return {
        "fps": fps_value,
        "history": fps_history
    }


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, threaded=True)
