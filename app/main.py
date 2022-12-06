"""
Fast API app for generating h3 grids.
"""

import math
import typing
import fastapi
import fastapi.middleware.cors
import fastapi.responses
import fastapi.staticfiles
import fastapi.templating
import geojson
import seeh3

app = fastapi.FastAPI(
    title="seeh3",
    description="Generates H3 grid for region",
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/seeh3"},
)

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", fastapi.staticfiles.StaticFiles(directory="static"), name="static")

templates = fastapi.templating.Jinja2Templates(directory="templates")

BB_REGEX = "^([+-]?[0-9]+(\.[0-9]+)?,?){4}$"


def _geth3_cells(
    resolution: typing.Optional[int] = None,
    exclude_poles: bool = True,
    bb: typing.Optional[str] = None,
    min_cells: int = 10,
) -> set[str]:
    if bb is not None:
        xmin, ymin, xmax, ymax = bb.split(",", 4)
        xmin = float(xmin)
        ymin = float(ymin)
        xmax = float(xmax)
        ymax = float(ymax)
        coords = [
            (xmin, ymax),
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
        ]
        return seeh3.geojson_polygon_to_h3cells(
            coords,
            min_cells=min_cells,
            resolution=resolution,
            exclude_poles=exclude_poles,
        )
    if resolution is None:
        resolution = 0
    return seeh3.global_h3cells(resolution=resolution, exclude_poles=exclude_poles)


# Shared query parameter definitions
resolution_q = fastapi.Query(
    default=None,
    ge=0,
    le=16,
    description="H3 resolution. Default is to infer from min_cells.",
)
exclude_poles_q = fastapi.Query(
    default=True, description="Exclude cells containing the north or south poles."
)
bb_q = fastapi.Query(
    default=None,
    regex=BB_REGEX,
    description="Bounding box for cells (minx, miny, maxx, maxy)",
    example="-150,-37,150,37",
)
min_cells_q = fastapi.Query(
    default=10, gt=0, lt=10000, description="Minimum number of cells to return."
)


@app.get(
    "/cells/",
    name="Get H3 cells",
    description="Return a list of H3 cell identifiers for the provided bounding box or globally.",
)
def get_h3_cells(
    resolution: typing.Optional[int] = resolution_q,
    exclude_poles: bool = exclude_poles_q,
    bb: typing.Optional[str] = bb_q,
    min_cells: int = min_cells_q,
) -> set[str]:
    return _geth3_cells(
        resolution=resolution, exclude_poles=exclude_poles, bb=bb, min_cells=min_cells
    )


@app.get(
    "/grid/",
    name="Get H3 GeoJSON grid",
    description="Return a GeoJSON feature collection of H3 cells for the provided bounding box or globally.",
)
def get_h3_grid(
    resolution: typing.Optional[int] = resolution_q,
    exclude_poles: bool = exclude_poles_q,
    bb: typing.Optional[str] = bb_q,
    min_cells: int = min_cells_q,
) -> geojson.FeatureCollection:
    cells = _geth3_cells(
        resolution=resolution, exclude_poles=exclude_poles, bb=bb, min_cells=min_cells
    )
    return seeh3.h3s_to_feature_collection(cells)


def clip_float(v: float, min_v: float, max_v: float) -> float:
    if v < min_v:
        return min_v
    if v > max_v:
        return max_v
    return v


def estimate_resolution(bb) -> int:
    if bb is None:
        return 1
    dx = abs(bb[2] - bb[0])
    if dx > 90:
        return 2
    if dx > 45:
        return 3
    if dx > 22:
        return 4
    if dx > 10:
        return 5
    if dx > 5:
        return 6
    if dx > 2:
        return 7
    if dx > 1:
        return 8
    if dx > 0.5:
        return 9
    if dx > 0.1:
        return 10
    return 10


@app.get(
    "/counts/",
    name="Get H3 GeoJSON grid of record counts",
    description=(
            "Return a GeoJSON feature collection of H3 cells for the "
            "provided bounding box or globally. "
            "bb is min_longitude, min_latitude, max_longitude, max_latitude"
    ),
)
def get_h3_grid(
    resolution: typing.Optional[int] = resolution_q,
    exclude_poles: bool = exclude_poles_q,
    bb: typing.Optional[str] = bb_q,
    q: str = None,
) -> geojson.FeatureCollection:
    fq = None
    if bb is not None and len(bb) > 4:
        bbox = bb.split(",")
        bbox = [float(v) for v in bbox]
        bbox[0] = clip_float(bbox[0], -180, 180)
        bbox[1] = clip_float(bbox[1], -90, 90)
        bbox[2] = clip_float(bbox[2], -180, 180)
        bbox[3] = clip_float(bbox[3], -90, 90)
        fq = f"producedBy_samplingSite_location_ll:[{bbox[1]},{bbox[0]} TO {bbox[3]},{bbox[2]}]"
        if q is None:
            q = fq
        else:
            q = f"{q} AND {fq}"
        if resolution is None:
            resolution = estimate_resolution(bbox)
    if q is None:
        q = "*:*"
    record_counts = seeh3.get_record_counts(
        query=q, resolution=resolution, exclude_poles=exclude_poles
    )
    return seeh3.h3s_to_feature_collection(
        set(record_counts.keys()), cell_props=record_counts
    )


@app.get("/3", response_class=fastapi.responses.HTMLResponse)
def default(request: fastapi.requests.Request):
    return templates.TemplateResponse("viewer3d.html", {"request": request})


@app.get("/", response_class=fastapi.responses.HTMLResponse)
def default(request: fastapi.requests.Request):
    return templates.TemplateResponse("viewer2d.html", {"request": request})
