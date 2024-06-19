import io

import pandas as pd
from celery import shared_task
from scipy.io import wavfile
from enf import signal_processing, match

from .s3 import download_file, delete_file
from .datasets import get_dataset


@shared_task(ignore_result=False)
def match_file(filename, dataset_name, year, month):
    try:
        dataset = get_dataset(dataset_name)

        grid_times, grid_enf = dataset.frequency_data(year, month)

        query_file = download_file(filename)
        query_fs, query_data = wavfile.read(io.BytesIO(query_file))

        if query_data.ndim > 1:
            query_data = query_data[:, 0]

        harmonic_n = 2
        new_fs = 300
        grid_frequency = dataset.nominal_freq

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
