import os
import uuid
import logging

import boto3
from celery.result import AsyncResult
from flask import request, Blueprint, abort, jsonify
from werkzeug.utils import secure_filename
from botocore.exceptions import NoCredentialsError

from .tasks import match_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}


@bp.get("/result/<task_id>")
def result(task_id: str) -> dict[str, object]:
    res = AsyncResult(task_id)

    ready = res.ready()

    return {
        "ready": ready,
        "successful": res.successful() if ready else None,
        "value": res.get() if ready else res.result,
    }


@bp.post("/match")
def match() -> dict[str, object]:
    if 'file' not in request.files:
        abort(400, 'No file part')

    file = request.files['file']

    if file.filename == '':
        abort(400, 'No selected file')

    if file and allowed_file(file.filename):
        filename = upload_file(file)
        task = match_file.delay(filename, 'eso', 2023, 2)

        return {"task_id": task.id}

    else:
        print('File type not allowed')
        abort(400)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_file(file):
    logger.info("Uploading file")
    s3 = boto3.client('s3')
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"

    s3_bucket_name = os.getenv('S3_BUCKET_NAME')
    s3.upload_fileobj(file, s3_bucket_name, unique_filename)
    logger.info("File uploaded")

    return unique_filename


@bp.get("/s3")
def check_s3():
    s3 = boto3.client('s3')
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")

    try:
        s3.head_bucket(Bucket=s3_bucket_name)
        logger.info("AWS credentials found and bucket is accessible")
        return jsonify({"message": "AWS credentials found and bucket is accessible"}), 200
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return jsonify({"error": "AWS credentials not found"}), 500
    except Exception as e:
        logger.error(f"Error checking bucket: {e}")
        return jsonify({"error": str(e)}), 500
