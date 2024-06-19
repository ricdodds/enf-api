import os
import io
import logging

import boto3

logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')
bucket_name = os.getenv('BUCKET_NAME')


def upload_file(file, filename):
    s3_client.upload_fileobj(file, bucket_name, filename)

    logger.info(f"File {bucket_name}[{filename}] uploaded")


def download_file(filename):
    file_obj = io.BytesIO()
    s3_client.download_fileobj(bucket_name, filename, file_obj)
    file_obj.seek(0)

    logger.info(f"File {bucket_name}[{filename}] downloaded")

    return file_obj.read()


def delete_file(filename):
    s3_client.delete_object(Bucket=bucket_name, Key=filename)
    logger.info(f"File {bucket_name}[{filename}] deleted")

