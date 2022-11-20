"""
Fast API app for generating h3 grids.
"""

import typing
import fastapi
import fastapi.middleware.cors
import fastapi.responses
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


@app.get("/")
def default():
    return fastapi.responses.RedirectResponse("/docs")
