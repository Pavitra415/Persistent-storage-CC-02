
import json
import os
import socket
import uuid

from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename

from flask import (
    Flask,
    redirect,
    render_template_string,
    request,
    url_for,
    flash,
    send_from_directory
)

from kubernetes import client, config


# --------------------------------------------------
# PERSISTENT STORAGE CONFIGURATION
# --------------------------------------------------

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "records.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# FLASK APPLICATION
# --------------------------------------------------

app = Flask(__name__)
app.secret_key = "persistent-storage-lab"


# --------------------------------------------------
# FILE UPLOAD CONFIGURATION
# --------------------------------------------------

UPLOAD_FOLDER = os.path.join(str(DATA_DIR), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf",
    "png", "jpg", "jpeg",
    "docx", "txt",
    "xlsx", "csv"
}

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# --------------------------------------------------
# DASHBOARD HTML
# --------------------------------------------------


# --------------------------------------------------
# DASHBOARD HTML
# --------------------------------------------------

PAGE = r'''
<!doctype html>
<html lang="en">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>Persistent Storage Dashboard</title>

<style>

:root {
    --ink: #172033;
    --muted: #68738a;
    --blue: #3157d5;
    --bg: #f4f6fb;
    --line: #e6eaf2;
    --green: #16845b;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    font-family: Segoe UI, Arial, sans-serif;
    color: var(--ink);
}

header {
    background: linear-gradient(120deg,#172554,#3157d5);
    color: white;
    padding: 30px max(22px,calc((100% - 1080px)/2));
}

header small {
    letter-spacing: 2px;
    text-transform: uppercase;
    opacity: .8;
    font-weight: 700;
}

header h1 {
    margin: 10px 0 5px;
    font-size: 30px;
}

header p {
    margin: 0;
    color: #dbe5ff;
}

main {
    max-width: 1080px;
    margin: 26px auto;
    padding: 0 20px;
}

.cards {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 15px;
    margin-bottom: 20px;
}

.card, .panel {
    background: white;
    border: 1px solid var(--line);
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 5px 18px #1b2b4a0b;
}

.card span {
    font-size: 13px;
    color: var(--muted);
}

.card strong {
    display: block;
    font-size: 19px;
    margin-top: 9px;
}

.status {
    color: var(--green);
}

.layout {
    display: grid;
    grid-template-columns: .9fr 1.1fr;
    gap: 18px;
}

h2 {
    font-size: 18px;
    margin: 0 0 15px;
}

.hint {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
}

label {
    display: block;
    font-weight: 650;
    font-size: 13px;
    margin: 14px 0 7px;
}

input, textarea {
    width: 100%;
    border: 1px solid #d8deea;
    border-radius: 9px;
    padding: 12px;
    font: inherit;
}

textarea {
    min-height: 100px;
    resize: vertical;
}

button {
    border: 0;
    border-radius: 9px;
    background: var(--blue);
    color: white;
    padding: 11px 16px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 12px;
}

button.delete {
    background: #fff0f0;
    color: #b42332;
    padding: 7px 10px;
    margin: 0;
}

button.delete-pod {
    background: #dc3545;
    color: white;
    padding: 12px 18px;
}

.record {
    border: 1px solid var(--line);
    border-radius: 11px;
    padding: 13px;
    margin-top: 10px;
}

.record-top {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: center;
}

.record p {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 10px 0 5px;
}

.record small {
    color: var(--muted);
}

.empty {
    padding: 25px;
    text-align: center;
    color: var(--muted);
    background: #f8f9fc;
    border-radius: 10px;
}

.flash {
    padding: 11px 14px;
    background: #eaf8f1;
    color: #126544;
    border-radius: 9px;
    margin-bottom: 14px;
}

.error {
    background: #fff0f0;
    color: #b42332;
}

footer {
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    padding: 24px;
}

@media(max-width:720px) {
    .cards, .layout {
        grid-template-columns: 1fr;
    }

    header h1 {
        font-size: 24px;
    }
}
<style>

    body {
        font-family: Arial;
    }

    .record {
        padding: 15px;
        border-radius: 8px;
    }

    /* New file download styling */

    .file-info {
        margin-top: 12px;
        padding: 12px;
        background: #f1f5f9;
        border-radius: 8px;
    }

    .download {
        display: inline-block;
        margin-top: 5px;
        padding: 8px 14px;
        background: #2563eb;
        color: white;
        text-decoration: none;
        border-radius: 6px;
        font-size: 13px;
    }

    .download:hover {
        background: #1d4ed8;
    }

</style>
</head>

<body>

<header>
    <small>Kubernetes Lab · Problem 12</small>

    <h1>Persistent Storage Dashboard</h1>

    <p>
        Test whether application data survives Pod deletion and recreation.
    </p>
</header>


<main>

{% with messages = get_flashed_messages() %}
    {% for message in messages %}
        <div class="flash">{{ message }}</div>
    {% endfor %}
{% endwith %}


<!-- STATUS CARDS -->

<section class="cards">

    <div class="card">
        <span>Storage mount</span>

        <strong class="status">
            ● {{ "Mounted" if mounted else "Not mounted" }}
        </strong>
    </div>

    <div class="card">
        <span>Current Pod</span>

        <strong>{{ pod_name }}</strong>
    </div>

    <div class="card">
        <span>Saved records</span>

        <strong>{{ records|length }}</strong>
    </div>

</section>


<!-- RECORD MANAGEMENT -->

<section class="layout">

    <div class="panel">

        <h2>Save new data</h2>

        <p class="hint">
            Records are written to /data/records.json,
            backed by the PersistentVolumeClaim.
        </p>

        <form method="POST" action="/add" enctype="multipart/form-data">
            <label>Record title</label>

            <input
                name="title"
                maxlength="80"
                required
                placeholder="e.g. Lab observation"
            >

            <label>Data / message</label>

            <textarea
                name="content"
                required
                placeholder="Enter data that should remain available..."
            ></textarea>
            <label>Upload File (Optional)</label>
            <input
                type="file"
                name="file"
                accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv"
            >

            <button type="submit">
                Save to persistent storage
            </button>

        </form>

    </div>


    <div class="panel">

        <h2>Stored records</h2>

        <p class="hint">
            Delete the Pod, wait for its replacement,
            then refresh this page. Records should remain.
        </p>

        {% if records %}

            {% for item in records %}

                <div class="record">

                    <div class="record-top">

                        <b>{{ item.title }}</b>

                        <form
                            method="post"
                            action="{{ url_for('delete_record', record_id=item.id) }}"
                            onsubmit="return confirm('Delete this record?')"
                        >

                            <button class="delete">
                                Delete
                            </button>

                        </form>

                    </div>

                    <p>{{ item.content }}</p>
                    {% if item.get('filename') %}

    <div class="file-info">

        <p>
            <strong>Attached File:</strong>
            {{ item.get('original_filename') }}
        </p>

        <a
            href="{{ url_for('download_file', filename=item.get('filename')) }}"
            class="download"
        >
            Download File
        </a>

    </div>

{% endif %}

                    <small>{{ item.created_at }}</small>

                </div>

            {% endfor %}

        {% else %}

            <div class="empty">
                No records yet. Add one to begin the persistence test.
            </div>

        {% endif %}

    </div>

</section>


<!-- NEW KUBERNETES POD MANAGEMENT SECTION -->

<section class="panel" style="margin-top:18px">

    <h2>Kubernetes Pod Management</h2>

    <p class="hint">
        Delete the current application Pod directly from this dashboard.
        Kubernetes Deployment will automatically create a replacement Pod.
    </p>

    <form
        method="post"
        action="{{ url_for('delete_pod') }}"
        onsubmit="return confirm('Are you sure you want to delete the running application Pod?')"
    >

        <button type="submit" class="delete-pod">
            Delete Application Pod
        </button>

    </form>

    <p class="hint">
        After deletion, wait for Kubernetes to create a replacement Pod.
        Refresh the dashboard to check the saved records.
    </p>

</section>


<!-- PERSISTENCE TEST -->

<section class="panel" style="margin-top:18px">

    <h2>Persistence test</h2>

    <ol class="hint">

        <li>Add a record and confirm it appears.</li>

        <li>Delete the application Pod using the button above.</li>

        <li>Wait for Kubernetes to create a replacement Pod.</li>

        <li>Refresh this page. The saved records should still appear,
        although the Pod name changes.</li>

    </ol>

</section>

</main>


<footer>
    PersistentVolume → PersistentVolumeClaim → Pod · Kubernetes Problem 12
</footer>

</body>
</html>
'''


# --------------------------------------------------
# STORAGE FUNCTIONS
# --------------------------------------------------

def load_records():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    except (json.JSONDecodeError, OSError):
        return []


def save_records(records):

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    DATA_FILE.write_text(
        json.dumps(records, indent=2),
        encoding="utf-8"
    )


# --------------------------------------------------
# DASHBOARD ROUTE
# --------------------------------------------------

@app.get("/")
def index():

    records = load_records()

    return render_template_string(
        PAGE,
        records=records,
        mounted=DATA_DIR.exists() and os.access(DATA_DIR, os.W_OK),
        pod_name=os.environ.get("POD_NAME", socket.gethostname())
    )


# --------------------------------------------------
# ADD RECORD
# --------------------------------------------------


@app.post("/add")
def add_record():

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    uploaded_file = request.files.get("file")

    if not title:
        flash("Please enter a title.")
        return redirect(url_for("index"))

    # Prepare file information
    saved_filename = None
    original_filename = None

    if uploaded_file and uploaded_file.filename:

        if not allowed_file(uploaded_file.filename):
            flash("Unsupported file format.")
            return redirect(url_for("index"))

        original_filename = secure_filename(uploaded_file.filename)

        # Generate a unique filename
        extension = original_filename.rsplit(".", 1)[1].lower()
        saved_filename = f"{uuid.uuid4().hex}.{extension}"

        # Save uploaded file inside persistent storage
        uploaded_file.save(
            os.path.join(UPLOAD_FOLDER, saved_filename)
        )

    records = load_records()

    records.insert(
        0,
        {
            "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
            "title": title,
            "content": content,
            "created_at": datetime.now().astimezone().strftime(
                "%d %b %Y, %I:%M %p"
            ),
            "filename": saved_filename,
            "original_filename": original_filename
        }
    )

    save_records(records)

    flash("Record and file saved to the mounted persistent volume.")

    return redirect(url_for("index"))


# --------------------------------------------------
# DELETE INDIVIDUAL RECORD
# --------------------------------------------------


@app.post("/delete/<record_id>")
def delete_record(record_id):

    records = load_records()

    # Find the record that needs to be deleted
    record_to_delete = next(
        (r for r in records if r.get("id") == record_id),
        None
    )

    if record_to_delete:

        # Delete its uploaded file, if one exists
        filename = record_to_delete.get("filename")

        if filename:
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            if os.path.isfile(file_path):
                os.remove(file_path)

        # Remove the record from records.json
        records = [
            r for r in records
            if r.get("id") != record_id
        ]

        save_records(records)

        flash("Record and its attached file deleted.")

    else:
        flash("Record not found.")

    return redirect(url_for("index"))

# --------------------------------------------------
# DOWNLOAD UPLOADED FILE
# --------------------------------------------------

@app.get("/download/<filename>")
def download_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=True
    )



# --------------------------------------------------
# NEW: DELETE KUBERNETES POD
# --------------------------------------------------

@app.post("/delete-pod")
def delete_pod():

    try:

        # Load credentials from the Kubernetes ServiceAccount
        config.load_incluster_config()

        v1 = client.CoreV1Api()

        pod_name = os.environ.get("POD_NAME")
        namespace = os.environ.get("POD_NAMESPACE", "default")

        if not pod_name:
            return "Pod name not found.", 500

        # Request deletion of the current application Pod
        v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                grace_period_seconds=10
            )
        )

        return """
        <!doctype html>
        <html>
        <head>
            <title>Pod Deletion Requested</title>
        </head>
        <body style="font-family:Arial;padding:40px">

            <h2>Pod deletion requested successfully!</h2>

            <p>
                Kubernetes Deployment will automatically create
                a replacement Pod.
            </p>

            <p>
                Wait approximately 20–30 seconds before reopening
                the dashboard.
            </p>

            <a href="/">Return to Dashboard</a>

        </body>
        </html>
        """

    except Exception as e:

        app.logger.exception("Pod deletion failed")

        return f"Error deleting Pod: {str(e)}", 500


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "storage_writable": os.access(DATA_DIR, os.W_OK)
    }


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    app.run(
        host="0.0.0.0",
        port=5000
    )
