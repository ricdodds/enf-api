from enf import eso
from flask import Blueprint, jsonify

bp = Blueprint("datasets", __name__, url_prefix="/datasets")

supported_datasets = {
    "eso": eso,
}


def get_dataset(name):
    if name not in supported_datasets:
        raise ValueError(f"Database '{name}' not found.")

    return supported_datasets[name]


@bp.get("")
def datasets():
    return jsonify({
        "datasets": list(supported_datasets.keys())
    })


@bp.get("/<dataset>")
def eso_dates(dataset: str):
    ds = get_dataset(dataset)
    resources = ds.get_resources()

    return jsonify({
        "months": list(resources.keys())
    })


@bp.get("/<dataset>/<int:year>/<int:month>")
def eso_enf(dataset: str, year: int, month: int):
    ds = get_dataset(dataset)
    t, f = ds.frequency_data(year, month)

    return jsonify({
        "times": t.astype(str).tolist(),
        "enf": f.tolist(),
    })
