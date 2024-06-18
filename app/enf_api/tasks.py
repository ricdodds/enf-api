import os
import io

import boto3
import pandas as pd
from celery import shared_task
from scipy.io import wavfile

from enf import eso, signal_processing, match


@shared_task(ignore_result=False)
def match_file(filename, db_name, year, month):
    try:
        db = get_db(db_name)

        grid_times, grid_enf = db.frequency_data(year, month)

        query_file = download_file(filename)
        query_fs, query_data = wavfile.read(io.BytesIO(query_file))

        if query_data.ndim > 1:
            query_data = query_data[:, 0]

        harmonic_n = 2
        new_fs = 300
        grid_frequency = db.nominal_freq

        low_cut = harmonic_n * grid_frequency - (grid_frequency - grid_enf.min())
        high_cut = harmonic_n * grid_frequency + (grid_enf.max() - grid_frequency)

        query_enf = signal_processing.enf_series(
            query_data, low_cut, high_cut, query_fs, new_fs
        )

        match_idx = match.stump(query_enf, grid_enf)[0][0]

        # return int(test_idx)
        return {
            "match_time": pd.to_datetime(str(grid_times[match_idx])).strftime('%Y-%m-%d %H:%M:%S'),
            "query_enf": query_enf.tolist(),
        }

    finally:
        delete_file(filename)


def delete_file(filename):
    s3 = boto3.client('s3')
    bucket_name = os.getenv("S3_BUCKET_NAME")

    s3.delete_object(Bucket=bucket_name, Key=filename)


def download_file(filename):
    s3 = boto3.client('s3')
    bucket_name = os.getenv("S3_BUCKET_NAME")

    file_obj = io.BytesIO()
    s3.download_fileobj(bucket_name, filename, file_obj)
    file_obj.seek(0)

    return file_obj.read()


def get_db(db_name):
    dbs = {'eso': eso}

    if db_name not in dbs:
        raise ValueError(f"Database '{db_name}' not found.")

    return dbs[db_name]
