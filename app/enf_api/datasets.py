from http.client import HTTPException
from datetime import datetime, timedelta, date

from enf import eso, gridradar
from flask import Blueprint, jsonify, request

from .db import fetch_from_db, save_to_db

bp = Blueprint("datasets", __name__, url_prefix="/datasets")

supported_datasets = {
    "eso": eso,
    "gridradar": gridradar,
}


@bp.get("")
def datasets():
    return jsonify({
        "datasets": list(supported_datasets.keys())
    })


def get_dataset(name):
    if name not in supported_datasets:
        raise ValueError(f"Database '{name}' not found.")

    return supported_datasets[name]


@bp.get("/<dataset>")
def dataset_enf(dataset: str):
    from_ts = request.args.get("from")
    to_ts = request.args.get("to") or from_ts

    from_dt = datetime.fromisoformat(from_ts).date()
    to_dt = datetime.fromisoformat(to_ts).date()

    return jsonify(query_range(dataset, from_dt, to_dt))


def query_range(dataset: str, from_dt: date, to_dt: date) -> list[tuple[str, float]]:
    if from_dt > to_dt:
        raise HTTPException("Invalid date range")

    number_of_days = (to_dt - from_dt).days + 1
    requested_dates = set(
        from_dt + timedelta(days=i) for i in range(number_of_days)
    )
    cached_data = fetch_from_db(dataset, from_dt, to_dt)
    cached_dates = set(r.timestamp.date() for r in cached_data)

    cached_data = [(r.timestamp.isoformat(), r.frequency) for r in cached_data]

    ds = get_dataset(dataset)

    missing_dates = requested_dates - cached_dates
    if missing_dates:
        new_data = ds.query_dates(list(missing_dates))
        save_to_db(dataset, new_data)

        cached_data.extend(new_data)

    return sorted(cached_data, key=lambda x: x[0])


@bp.get("/<dataset>/range")
def dataset_range(dataset: str):
    ds = get_dataset(dataset)

    resources = ds.get_resources()

    return jsonify({
        "months": list(resources.keys())
    })
