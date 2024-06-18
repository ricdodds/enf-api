from typing import List, Tuple, Any

from flask import Blueprint

from enf import eso as eso_data

dbp = Blueprint("data", __name__, url_prefix="/data")


@dbp.get("/")
def datasource() -> List[str]:
    return ["eso"]


@dbp.get("/eso")
def eso() -> list[Tuple]:
    resources = eso_data.get_resources()

    return list(resources.keys())


@dbp.get("/eso/<int:year>/<int:month>")
def eso_enf(year: int, month: int) -> dict[str, Any]:
    t, f = eso_data.frequency_data(year, month)

    return {
        "times": t.astype(str).tolist(),
        "enf": f.tolist(),
    }
