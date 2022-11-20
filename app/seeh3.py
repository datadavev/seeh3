import typing
import antimeridian_splitter
import geojson
import h3

# These are H3 cells from resolutions 0-16 that overlap the north or south poles
POLES = {
    "8af2939520c7fff",
    "8df2939520864bf",
    "8e03262a696431f",
    "8903262a697ffff",
    "8bf2939520c6fff",
    "80f3fffffffffff",
    "8cf2939520c69ff",
    "8503262bfffffff",
    "8d03262a4490cff",
    "8403263ffffffff",
    "8c03262a4490dff",
    "8803262a69fffff",
    "81f2bffffffffff",
    "81033ffffffffff",
    "8703262a6ffffff",
    "8a03262a6967fff",
    "83f293fffffffff",
    "84f2939ffffffff",
    "8af293952087fff",
    "85f29383fffffff",
    "89f2939520bffff",
    "8b03262a4490fff",
    "8df2939520c687f",
    "8003fffffffffff",
    "8e03262a4490cf7",
    "830326fffffffff",
    "8a03262a4497fff",
    "89f2939520fffff",
    "8bf293952086fff",
    "87f293952ffffff",
    "8b03262a6964fff",
    "88f2939521fffff",
    "8c03262a69643ff",
    "8903262a44bffff",
    "8603262a7ffffff",
    "8ef2939520864f7",
    "8cf2939520865ff",
    "86f293957ffffff",
    "820327fffffffff",
    "8d03262a696433f",
    "82f297fffffffff",
    "8ef2939520c684f",
}


def h3_to_features(cell: str) -> list[geojson.Feature]:
    """Given a h3 cell, return one or more geojson Features representing the cell.

    More than one feature may be returned if the polygon is split on the
    anti-meridian.

    Features are returned with properties:
      h3 = the cell
      km2 = the area of the cell in km^2
    """
    polygon = geojson.MultiPolygon(
        [
            h3.cell_to_boundary(cell, geo_json=True),
        ]
    )
    split_polygons = antimeridian_splitter.split_polygon(
        polygon, output_format="geojsondict"
    )
    res = []
    for p in split_polygons:
        res.append(
            geojson.Feature(
                geometry=p,
                properties={
                    "h3": cell,
                    "km2": h3.cell_area(cell, unit="km^2"),
                },
            )
        )
    return res


def h3s_to_feature_collection(cells: set[str]) -> geojson.FeatureCollection:
    """Returns the geojson feature collection representing the provided h3 cells.

    Cell polygons may be split on the anti-meridian.
    """
    features = []
    for cell in cells:
        features += h3_to_features(cell)
    return geojson.FeatureCollection(features)


def geojson_polygon_to_h3cells(
    coordinates: typing.Sequence[typing.Sequence[float]],
    min_cells: int = 10,
    resolution: typing.Optional[int] = None,
    exclude_poles:bool = True
) -> set[str]:
    """H3 cells in polygon.

    If resolution is not set, the resolution is increased until the
    number of cells exceeds min_cells.

    Note: h3 4.0.0b1 expects latitude,longitude coordinate order :(
    https://github.com/uber/h3-py/blob/master/src/h3/api/_api_template.py

    https://uber.github.io/h3-py/api_reference.html#h3.polygon_to_cells
    """
    _p = []
    for lat, lng in coordinates:
        _p.append(
            (
                lng,
                lat,
            )
        )
    polygon = h3.Polygon(_p)
    res = set()
    if resolution is not None:
        res = set(h3.polygon_to_cells(polygon, resolution))
    else:
        resolution = 0
        n_cells = 0
        while n_cells < min_cells and resolution < 16:
            res = set(h3.polygon_to_cells(polygon, resolution))
            n_cells = len(res)
            resolution += 1
    if not exclude_poles:
        return res
    return res.difference(POLES)


def global_h3cells(resolution=0, exclude_poles:bool=True)->set[str]:
    '''List of all h3 cells at specified resolution (max 4).
    '''
    if resolution < 0:
        resolution = 0
    cells = h3.get_res0_cells()
    if resolution == 0:
        if exclude_poles:
            return cells.difference(POLES)
        return cells
    if resolution > 4:
        resolution = 4
    _cells = set()
    for cell in cells:
        children = h3.cell_to_children(cell, res=resolution)
        if exclude_poles:
            _cells.update(children.difference(POLES))
        else:
            _cells.update(children)
    return _cells
