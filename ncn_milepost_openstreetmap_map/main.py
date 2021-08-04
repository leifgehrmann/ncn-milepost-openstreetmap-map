import cairocffi
from map_engraver.data.osm import Element, Node
from map_engraver.data.osm.filter import filter_elements
from map_engraver.data.osm.parser import Parser
from map_engraver.drawable.geometry.symbol_drawer import SymbolDrawer
from map_engraver.graphicshelper import CairoHelper
from map_engraver.transformers.osm_to_shapely import OsmToShapely, OsmPoint
from typing import List, Union, Tuple, Optional

import pyproj
from shapely import ops
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, shape, MultiPolygon, Point
from map_engraver.drawable.geometry.polygon_drawer import PolygonDrawer
from map_engraver.drawable.layout.background import Background
from map_engraver.transformers.geo_canvas_scale import GeoCanvasScale
from map_engraver.transformers.geo_canvas_transformers import \
    build_geo_to_canvas_transformer
from map_engraver.transformers.geo_coordinate import GeoCoordinate
from pathlib import Path
import os
import urllib.request
import urllib.parse
import zipfile
import shutil

import shapefile

from map_engraver.canvas import CanvasBuilder, Canvas
from map_engraver.canvas.canvas_unit import CanvasUnit


# 1. Download Natural Earth shapefiles. In non-master GitHub Actions, use mock
#    coastline data.
def download_and_extract_shape(url):
    # Create cache directory if it does not exist.
    cache_path = Path(__file__).parent.parent.joinpath('cache/')
    cache_path.mkdir(parents=True, exist_ok=True)

    # Declare file paths. The filenames are inferred from the url, so this
    # logic could be brittle to changes.
    zip_name = url.split('/')[-1]
    extract_name = url.split('/')[-1].split('.')[0]
    shp_name = extract_name + '.shp'
    dbf_name = extract_name + '.dbf'
    zip_path = cache_path.joinpath(zip_name)
    extract_path = cache_path.joinpath(extract_name)
    extract_shp_path = extract_path.joinpath(shp_name)
    extract_dbf_path = extract_path.joinpath(dbf_name)
    shp_path = cache_path.joinpath(shp_name)
    dbf_path = cache_path.joinpath(dbf_name)

    # Check if Shapefile already exists. Skip if it does.
    if shp_path.exists() and dbf_path.exists():
        return

    # Download the ZIP to the cache.
    data = urllib.request.urlopen(url)
    data = data.read()
    file = open(zip_path.as_posix(), 'wb')
    file.write(data)
    file.close()

    # Extract the ZIP within the cache.
    with zipfile.ZipFile(zip_path.as_posix()) as zf:
        zf.extractall(extract_path.as_posix())

    # Move Shapefile out of the extract directory to the cache directory.
    os.rename(extract_shp_path.as_posix(), shp_path.as_posix())
    os.rename(extract_dbf_path.as_posix(), dbf_path.as_posix())

    # Delete ZIP and Extract.
    os.unlink(zip_path.as_posix())
    shutil.rmtree(extract_path.as_posix())


ne_root_url = 'https://www.naturalearthdata.com/' \
              'http//www.naturalearthdata.com/download/'
ne_land_url = ne_root_url + '10m/physical/ne_10m_land.zip'
ne_islands_url = ne_root_url + '10m/physical/ne_10m_minor_islands.zip'
ne_lakes_url = ne_root_url + '10m/physical/ne_10m_lakes.zip'
ne_lakes_eu_url = ne_root_url + '10m/physical/ne_10m_lakes_europe.zip'
ne_urban_url = ne_root_url + '10m/cultural/ne_10m_urban_areas.zip'
download_and_extract_shape(ne_land_url)
download_and_extract_shape(ne_islands_url)
download_and_extract_shape(ne_lakes_url)
download_and_extract_shape(ne_lakes_eu_url)
download_and_extract_shape(ne_urban_url)


# 1.1 Convert Shapefiles to shapely geometry.
def parse_shapefile(shapefile_name: str):
    cache_path = Path(__file__).parent.parent.joinpath('cache')
    shapefile_path = cache_path.joinpath(shapefile_name)
    shapefile_collection = shapefile.Reader(shapefile_path.as_posix())
    shapely_objects = []
    for shape_record in shapefile_collection.shapeRecords():
        shapely_objects.append(shape(shape_record.shape.__geo_interface__))
    return shapely_objects


land_shapes = parse_shapefile('ne_10m_land.shp')
island_shapes = parse_shapefile('ne_10m_minor_islands.shp')
lake_shapes = parse_shapefile('ne_10m_lakes.shp')
lake_eu_shapes = parse_shapefile('ne_10m_lakes_europe.shp')
urban_shapes = parse_shapefile('ne_10m_urban_areas.shp')


# Invert CRS for shapes, because shape files are dumb
def transform_geom_to_invert(geom: BaseGeometry):
    new_geom = ops.transform(lambda x, y: (y, x), geom)
    if isinstance(geom, OsmPoint):
        new_geom = OsmPoint(new_geom)
        new_geom.osm_tags = geom.osm_tags
    return new_geom


def transform_geoms_to_invert(geoms: List[BaseGeometry]):
    return list(map(lambda geom: transform_geom_to_invert(geom), geoms))


land_shapes = transform_geoms_to_invert(land_shapes)
island_shapes = transform_geoms_to_invert(island_shapes)
lake_shapes = transform_geoms_to_invert(lake_shapes)
lake_eu_shapes = transform_geoms_to_invert(lake_eu_shapes)
urban_shapes = transform_geoms_to_invert(urban_shapes)


# 2. Download OpenStreetMap milepost data. In GitHub Actions, use mock milepost
#    data.
def download_mileposts():
    osm_path = Path(__file__).parent.parent.joinpath('cache/mileposts.osm')
    if osm_path.exists():
        return
    bbox = '%f,%f,%f,%f' % (49.9599, -8.1956, 60.8842, 1.7746)
    query = '''[timeout:25];(node[ncn_milepost](%s););out;''' % bbox
    url_encoded_query = urllib.parse.urlencode({'data': query})
    url = 'http://overpass-api.de/api/interpreter?%s' % url_encoded_query
    data = urllib.request.urlopen(url).read().decode()
    file = open(osm_path.as_posix(), 'w+')
    file.write(data)
    file.close()


download_mileposts()


# clip any geoms that appear outside of the geometry
def clip_polygons(
        polygons: List[Polygon],
        clip_polygon: Polygon
) -> List[Union[Polygon, MultiPolygon]]:
    output = []
    for polygon in polygons:
        polygon_intersection = polygon.intersection(clip_polygon)
        if not polygon_intersection.is_empty:
            output.append(polygon_intersection)
    return output


british_isles_clip_polygon = Polygon([
    (48, -12),
    (62, -12),
    (62, 4),
    (48, 4),
    (48, -12)
])
land_shapes = clip_polygons(land_shapes, british_isles_clip_polygon)
island_shapes = clip_polygons(island_shapes, british_isles_clip_polygon)
lake_shapes = clip_polygons(lake_shapes, british_isles_clip_polygon)
lake_eu_shapes = clip_polygons(lake_eu_shapes, british_isles_clip_polygon)
urban_shapes = clip_polygons(urban_shapes, british_isles_clip_polygon)


# Subtract lakes from land
def subtract_lakes_from_land(land: Polygon, lakes: List[Polygon]):
    for lake in lakes:
        land = land.difference(lake)
    return land


land_shapes = list(map(
    lambda geom: subtract_lakes_from_land(geom, lake_shapes),
    land_shapes
))
land_shapes = list(map(
    lambda geom: subtract_lakes_from_land(geom, lake_eu_shapes),
    land_shapes
))

# Project coordinates to canvas
wgs84_crs = pyproj.CRS.from_epsg(4326)
british_crs = pyproj.CRS.from_epsg(27700)
geo_canvas_scale = GeoCanvasScale(800000, CanvasUnit.from_px(720))
origin_for_geo = GeoCoordinate(-50000, 1225000, british_crs)
wgs84_canvas_transformer = build_geo_to_canvas_transformer(
    crs=british_crs,
    scale=geo_canvas_scale,
    origin_for_geo=origin_for_geo,
    data_crs=wgs84_crs
)


# Transform array of polygons to canvas:
def transform_geom_to_canvas(geom: BaseGeometry):
    new_geom = ops.transform(wgs84_canvas_transformer, geom)
    if isinstance(geom, OsmPoint):
        new_geom = OsmPoint(new_geom)
        new_geom.osm_tags = geom.osm_tags
    return new_geom


def transform_geoms_to_canvas(geoms: List[BaseGeometry]) -> List[BaseGeometry]:
    return list(map(transform_geom_to_canvas, geoms))


land_shapes = transform_geoms_to_canvas(land_shapes)
island_shapes = transform_geoms_to_canvas(island_shapes)
urban_shapes = transform_geoms_to_canvas(urban_shapes)


# Parse mileposts
def filter_mileposts(_, element: Element) -> bool:
    if isinstance(element, Node):
        return 'ncn_milepost' in element.tags
    return False


milepost_osm_path = Path(__file__).parent.parent.joinpath('cache/mileposts.osm')
milepost_osm = Parser().parse(milepost_osm_path)
milepost_osm_subset = filter_elements(milepost_osm, filter_mileposts)
milepost_osm_to_shapely = OsmToShapely(milepost_osm)
milepost_points = milepost_osm_to_shapely.nodes_to_points(
    milepost_osm_subset.nodes
)
milepost_points = transform_geoms_to_invert(milepost_points)
milepost_points = transform_geoms_to_canvas(milepost_points)


# 3. Render the map (Later, create a dark-mode variant)
Path(__file__).parent.parent.joinpath('output/') \
    .mkdir(parents=True, exist_ok=True)
path = Path(__file__).parent.joinpath('../output/map.svg')
path.unlink(missing_ok=True)
canvas_builder = CanvasBuilder()
canvas_builder.set_path(path)
canvas_builder.set_size(CanvasUnit.from_px(720), CanvasUnit.from_px(1110))
canvas = canvas_builder.build()
# 3.0 Background
bg = Background()
bg.color = (0.8, 0.9, 1)
bg.draw(canvas)
# 3.1.1 Land and Islands
land_drawer = PolygonDrawer()
land_drawer.geoms = land_shapes
island_drawer = PolygonDrawer()
island_drawer.geoms = island_shapes

canvas.context.set_line_join(cairocffi.LINE_JOIN_ROUND)
land_drawer.fill_color = None
land_drawer.stroke_color = (0.75, 0.85, 0.95)
land_drawer.stroke_width = CanvasUnit.from_px(3)
land_drawer.draw(canvas)
island_drawer.fill_color = None
island_drawer.stroke_color = (0.75, 0.85, 0.95)
island_drawer.stroke_width = CanvasUnit.from_px(3)
island_drawer.draw(canvas)

land_drawer.stroke_width = CanvasUnit.from_px(1)
land_drawer.stroke_color = (0.5, 0.6, 0.7)
land_drawer.draw(canvas)
island_drawer.stroke_width = CanvasUnit.from_px(1)
island_drawer.stroke_color = (0.5, 0.6, 0.7)
island_drawer.draw(canvas)

land_drawer.stroke_color = None
land_drawer.fill_color = (1, 1, 1)
land_drawer.draw(canvas)
island_drawer.stroke_color = None
island_drawer.fill_color = (1, 1, 1)
island_drawer.draw(canvas)
# 3.2 Urban Areas
urban_drawer = PolygonDrawer()
urban_drawer.geoms = urban_shapes
urban_drawer.fill_color = (0.95, 0.95, 0.95)
urban_drawer.draw(canvas)


# 3.3 Milepost Symbols
class MilepostDrawer(SymbolDrawer):
    def __init__(self):
        super().__init__()
        self.size = CanvasUnit.from_px(10).pt

    @staticmethod
    def get_colors(point: OsmPoint) -> Tuple[
        Optional[Tuple[float, float, float, float]],
        Optional[Tuple[float, float, float, float]]
    ]:
        if 'ncn_milepost' not in point.osm_tags:
            return None, None
        if point.osm_tags['ncn_milepost'] == 'mills':  # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 = Red
            return (
                (0.9, 0.3, 0.3, 0.6),
                (0.7, 0.0, 0.0, 1)
            )
        if point.osm_tags['ncn_milepost'] == 'rowe':  # 🏴󠁧󠁢󠁷󠁬󠁳󠁿 = Green
            return (
                (0, 0.9, 0, 0.6),
                (0, 0.7, 0, 1)
            )
        if point.osm_tags['ncn_milepost'] == 'mccoll':  # 🏴󠁧󠁢󠁳󠁣󠁴󠁿 = Blue
            return (
                (0, 0.6, 1, 0.6),
                (0, 0.4, 0.7, 1)
            )
        if point.osm_tags['ncn_milepost'] == 'dudgeon':  # Ireland = Yellow
            return (
                (1, 0.9, 0, 0.6),
                (0.8, 0.7, 0, 1)
            )
        return None, None

    def draw_symbol(self, point: Point, canvas: Canvas):
        if not isinstance(point, OsmPoint):
            return

        fill, stroke = self.get_colors(point)
        if fill is None:
            return

        canvas.context.set_source_rgba(*fill)
        CairoHelper.draw_circle(
            canvas.context,
            point,
            CanvasUnit.from_px(6).pt
        )
        canvas.context.fill_preserve()
        canvas.context.set_line_width(CanvasUnit.from_px(0.5).pt)
        canvas.context.set_source_rgba(*stroke)
        canvas.context.stroke()


milepost_drawer = MilepostDrawer()
milepost_drawer.points = milepost_points
milepost_drawer.draw(canvas)

# 3.4 Title and Labels
# 3.5 Margins
canvas.close()
