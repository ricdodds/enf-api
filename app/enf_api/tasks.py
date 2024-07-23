import io

import pandas as pd
from celery import shared_task
from scipy.io import wavfile
from enf import signal_processing, match

from .datasets import query_range
from .s3 import download_file, delete_file


@shared_task(ignore_result=False)
def match_file(filename, dataset_name, from_ts, to_ts):

    try:
        from_dt = pd.to_datetime(from_ts).date()
        to_dt = pd.to_datetime(to_ts).date()

        data = query_range(dataset_name, from_dt, to_dt)
        grid_times, grid_enf = zip(*data)

        query_file = download_file(filename)
        query_fs, query_data = wavfile.read(io.BytesIO(query_file))

        if query_data.ndim > 1:
            query_data = query_data[:, 0]

        harmonic_n = 2
        new_fs = 300
        grid_frequency = 50

        low_cut = harmonic_n * grid_frequency - (grid_frequency - min(grid_enf))
        high_cut = harmonic_n * grid_frequency + (max(grid_enf) - grid_frequency)

        query_enf = signal_processing.enf_series(
            query_data, low_cut, high_cut, query_fs, new_fs
        )

        match_idx = match.stump(query_enf, grid_enf)[0][0]

        # return int(test_idx)
        return {
            "match_time": pd.to_datetime(
                str(grid_times[match_idx])
            ).strftime('%Y-%m-%d %H:%M:%S'),
            "query_enf": query_enf.tolist(),
        }

    finally:
        delete_file(filename)
