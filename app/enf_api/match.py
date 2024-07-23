import uuid
import logging

from celery.result import AsyncResult
from flask import request, Blueprint, jsonify
from werkzeug.utils import secure_filename

from .tasks import match_file
from .s3 import upload_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint("match", __name__, url_prefix="/match")

ALLOWED_EXTENSIONS = {'wav'}


@bp.post("")
def match():
    db_name = request.args.get("db")
    from_ts = request.args.get("from")
    to_ts = request.args.get("to") or from_ts

    if not db_name or not from_ts:
        return jsonify({"error": "Missing required query parameters"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"

        upload_file(file, unique_filename)
        task = match_file.delay(unique_filename, db_name, from_ts, to_ts)

        logger.info(f"Task enf_api.tasks.match_file[{task.id}] submitted")

        return jsonify({"task_id": task.id})

    else:
        return jsonify({"error": "File type not allowed"}), 400


@bp.get("/result/<task_id>")
def result(task_id: str):
    res = AsyncResult(task_id)

    ready = res.ready()

    return jsonify({
        "ready": ready,
        "successful": res.successful() if ready else None,
        "value": res.get() if ready else res.result,
    })


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
