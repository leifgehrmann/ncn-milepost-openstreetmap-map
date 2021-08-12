from datetime import datetime

import cairocffi
import pangocffi
from map_engraver.canvas.canvas_coordinate import CanvasCoordinate
from map_engraver.data.osm import Element, Node
from map_engraver.data.osm.filter import filter_elements
from map_engraver.data.osm.parser import Parser
from map_engraver.data.pango.layout import Layout
from map_engraver.drawable.text.pango_drawer import PangoDrawer
from map_engraver.graphicshelper import CairoHelper
from map_engraver.data.osm_shapely.osm_to_shapely import OsmToShapely
from map_engraver.data.osm_shapely.osm_point import OsmPoint
from typing import List, Union, Tuple

import pyproj
from shapely import ops
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, shape, MultiPolygon, Point
from map_engraver.drawable.geometry.polygon_drawer import PolygonDrawer
from map_engraver.drawable.layout.background import Background
from map_engraver.data import geo_canvas_ops, osm_shapely_ops
from map_engraver.data.geo.geo_coordinate import GeoCoordinate
from pathlib import Path

import shapefile

from map_engraver.canvas import CanvasBuilder
from map_engraver.canvas.canvas_unit import CanvasUnit

from ncn_milepost_openstreetmap_map.data_retriever import download_and_extract_shape, download_mileposts
from ncn_milepost_openstreetmap_map.milepost_drawer import MilepostDrawer

import sys


mode = 'light'
if '--dark' in sys.argv:
    mode = 'dark'

background_fill_color = (184/255, 224/255, 243/255, 1)
land_fill_color = (1, 1, 1, 1)
urban_fill_color = (0.95, 0.95, 0.95, 1)
text_fill_color = (0, 0, 0, 1)
if mode == 'dark':
    background_fill_color = (17 / 255, 17 / 255, 17 / 255, 1)
    land_fill_color = (65/255, 65/255, 65/255, 1)
    urban_fill_color = (74/255, 74/255, 74/255, 1)
    text_fill_color = (0.9, 0.9, 0.9, 1)


# 1. Download Natural Earth shapefiles. In non-master GitHub Actions, use mock
#    coastline data.
ne_root_url = 'https://www.naturalearthdata.com/' \
              'http//www.naturalearthdata.com/download/'
ne_land_url = ne_root_url + '10m/physical/ne_10m_land.zip'
ne_islands_url = ne_root_url + '10m/physical/ne_10m_minor_islands.zip'
ne_lakes_url = ne_root_url + '10m/physical/ne_10m_lakes.zip'
ne_lakes_eu_url = ne_root_url + '10m/physical/ne_10m_lakes_europe.zip'
ne_urban_url = ne_root_url + '10m/cultural/ne_10m_urban_areas.zip'
# TODO: download_and_extract_shape(ne_land_url)
# TODO: download_and_extract_shape(ne_islands_url)
# TODO: download_and_extract_shape(ne_lakes_url)
# TODO: download_and_extract_shape(ne_lakes_eu_url)
# TODO: download_and_extract_shape(ne_urban_url)


# 1.1 Convert Shapefiles to shapely geometry.
def parse_shapefile(shapefile_name: str):
    cache_path = Path(__file__).parent.parent.joinpath('cache')
    shapefile_path = cache_path.joinpath(shapefile_name)
    shapefile_collection = shapefile.Reader(shapefile_path.as_posix())
    shapely_objects = []
    for shape_record in shapefile_collection.shapeRecords():
        shapely_objects.append(shape(shape_record.shape.__geo_interface__))
    return shapely_objects


# TODO: land_shapes = parse_shapefile('ne_10m_land.shp')
# TODO: island_shapes = parse_shapefile('ne_10m_minor_islands.shp')
# TODO: lake_shapes = parse_shapefile('ne_10m_lakes.shp')
# TODO: lake_eu_shapes = parse_shapefile('ne_10m_lakes_europe.shp')
# TODO: urban_shapes = parse_shapefile('ne_10m_urban_areas.shp')
land_shapes = []
island_shapes = []
lake_shapes = []
lake_eu_shapes = []
urban_shapes = []


# Invert CRS for shapes, because shapefiles are store coordinates are lon/lat,
# not according to the ISO-approved standard.
def transform_geoms_to_invert(geoms: List[BaseGeometry]):
    return list(map(
        lambda geom: ops.transform(lambda x, y: (y, x), geom),
        geoms
    ))


land_shapes = transform_geoms_to_invert(land_shapes)
island_shapes = transform_geoms_to_invert(island_shapes)
lake_shapes = transform_geoms_to_invert(lake_shapes)
lake_eu_shapes = transform_geoms_to_invert(lake_eu_shapes)
urban_shapes = transform_geoms_to_invert(urban_shapes)


# 2. Download OpenStreetMap milepost data. In GitHub Actions, use mock milepost
#    data.
# TODO: download_mileposts()


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
geo_width = 800000  # In meters
canvas_width = CanvasUnit.from_px(720)
canvas_height = CanvasUnit.from_px(1180)
geo_canvas_scale = geo_canvas_ops.GeoCanvasScale(geo_width, canvas_width)
origin_for_geo = GeoCoordinate(-80000, 1225000, british_crs)
wgs84_canvas_transformer = geo_canvas_ops.build_transformer(
    crs=british_crs,
    scale=geo_canvas_scale,
    origin_for_geo=origin_for_geo,
    data_crs=wgs84_crs
)


# Transform array of polygons to canvas:
def transform_geom_to_canvas(geom: BaseGeometry):
    if isinstance(geom, OsmPoint):
        return osm_shapely_ops.transform(wgs84_canvas_transformer, geom)
    else:
        return ops.transform(wgs84_canvas_transformer, geom)


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


# TODO: milepost_osm_path = Path(__file__).parent.parent.joinpath('cache/mileposts.osm')
# TODO: milepost_osm = Parser().parse(milepost_osm_path)
# TODO: milepost_osm_subset = filter_elements(milepost_osm, filter_mileposts)
# TODO: milepost_osm_to_shapely = OsmToShapely(milepost_osm)
# TODO: milepost_points = milepost_osm_to_shapely.nodes_to_points(
# TODO:     milepost_osm_subset.nodes
# TODO: )
# TODO: milepost_points = transform_geoms_to_canvas(milepost_points)
milepost_points = []


# 3. Render the map (Later, create a dark-mode variant)
Path(__file__).parent.parent.joinpath('output/') \
    .mkdir(parents=True, exist_ok=True)
path = Path(__file__).parent.joinpath('../output/map-%s.svg' % mode)
path.unlink(missing_ok=True)
canvas_builder = CanvasBuilder()
canvas_builder.set_path(path)
canvas_builder.set_size(canvas_width, canvas_height)
canvas = canvas_builder.build()
# 3.0 Background
bg = Background()
bg.color = background_fill_color
bg.draw(canvas)
# 3.1.1 Land and Islands
land_drawer = PolygonDrawer()
land_drawer.geoms = land_shapes
island_drawer = PolygonDrawer()
island_drawer.geoms = island_shapes

canvas.context.set_line_join(cairocffi.LINE_JOIN_ROUND)

land_drawer.stroke_color = None
land_drawer.fill_color = land_fill_color
land_drawer.draw(canvas)
island_drawer.stroke_color = None
island_drawer.fill_color = land_fill_color
island_drawer.draw(canvas)
# 3.2 Urban Areas
urban_drawer = PolygonDrawer()
urban_drawer.geoms = urban_shapes
urban_drawer.fill_color = urban_fill_color
urban_drawer.draw(canvas)


# 3.3 Milepost Symbols
milepost_drawer = MilepostDrawer()
milepost_drawer.points = milepost_points
milepost_drawer.draw(canvas)

# 3.4 Title and Labels
text_margin = CanvasUnit.from_px(40)
title_font = pangocffi.FontDescription()
title_font.set_family('Helvetica')
title_font.set_weight(pangocffi.Weight.BOLD)
title_font.set_size(CanvasUnit.from_px(16).pango)
date_font = pangocffi.FontDescription()
date_font.set_family('Helvetica')
date_font.set_weight(pangocffi.Weight.NORMAL)
date_font.set_size(CanvasUnit.from_px(12).pango)
legend_font = pangocffi.FontDescription()
legend_font.set_family('Helvetica')
legend_font.set_weight(pangocffi.Weight.NORMAL)
legend_font.set_size(CanvasUnit.from_px(12).pango)

title = Layout(canvas)
title.pango_layout.set_font_description(title_font)
title.pango_layout.set_spacing(CanvasUnit.from_px(6).pango)
title.set_markup('Millennium Mileposts in the United Kingdom by Type')
title.color = text_fill_color
title.position = CanvasCoordinate.from_px(text_margin.px, text_margin.px)
title.width = CanvasUnit.from_px(300)

date = Layout(canvas)
date.pango_layout.set_font_description(date_font)
date.set_markup(datetime.now().strftime('Last Updated: %Y-%m-%d'))
date.width = canvas_width
date.color = text_fill_color
date.position = CanvasCoordinate.from_px(
    text_margin.px,
    (canvas_height - date.logical_extents.height - text_margin).px
)

legend_r1_c1 = Layout(canvas)
legend_r1_c1.pango_layout.set_font_description(legend_font)
legend_r1_c1.set_text('Mills')
legend_r1_c1.color = text_fill_color
legend_r1_c2 = Layout(canvas)
legend_r1_c2.pango_layout.set_font_description(legend_font)
legend_r1_c2.set_text('Rowe')
legend_r1_c2.color = text_fill_color
legend_r2_c1 = Layout(canvas)
legend_r2_c1.pango_layout.set_font_description(legend_font)
legend_r2_c1.set_text('McColl')
legend_r2_c1.color = text_fill_color
legend_r2_c2 = Layout(canvas)
legend_r2_c2.pango_layout.set_font_description(legend_font)
legend_r2_c2.set_text('Dudgeon')
legend_r2_c2.color = text_fill_color

legend_c1_x = text_margin
legend_c2_x = legend_c1_x + title.width / 3

legend_r1_y = title.position.y + title.logical_extents.height
legend_r1_y += CanvasUnit.from_px(20)

legend_r2_y = legend_r1_y + CanvasUnit.from_px(12) + CanvasUnit.from_px(20)

legend_sym_width = CanvasUnit.from_px(12)
legend_text_height = legend_r1_c1.logical_extents.height

legend_r1_c1_sym = CanvasCoordinate(legend_c1_x + legend_sym_width / 2, legend_r1_y + legend_text_height / 2.5)
legend_r1_c2_sym = CanvasCoordinate(legend_c2_x + legend_sym_width / 2, legend_r1_y + legend_text_height / 2.5)
legend_r2_c1_sym = CanvasCoordinate(legend_c1_x + legend_sym_width / 2, legend_r2_y + legend_text_height / 2.5)
legend_r2_c2_sym = CanvasCoordinate(legend_c2_x + legend_sym_width / 2, legend_r2_y + legend_text_height / 2.5)
legend_r1_c1.position = CanvasCoordinate(legend_r1_c1_sym.x + legend_sym_width, legend_r1_y)
legend_r1_c2.position = CanvasCoordinate(legend_r1_c2_sym.x + legend_sym_width, legend_r1_y)
legend_r2_c1.position = CanvasCoordinate(legend_r2_c1_sym.x + legend_sym_width, legend_r2_y)
legend_r2_c2.position = CanvasCoordinate(legend_r2_c2_sym.x + legend_sym_width, legend_r2_y)

title_drawer = PangoDrawer()
title_drawer.pango_objects = [
    title,
    date,
    legend_r1_c1,
    legend_r1_c2,
    legend_r2_c1,
    legend_r2_c2
]
title_drawer.draw(canvas)


def draw_legend_circle(
        point: CanvasCoordinate,
        fill: Tuple[float, float, float, float],
        stroke: Tuple[float, float, float, float]
):
    canvas.context.set_source_rgba(*fill)
    CairoHelper.draw_circle(
        canvas.context,
        Point(point.x.pt, point.y.pt),
        CanvasUnit.from_px(12).pt
    )
    canvas.context.fill()
    CairoHelper.draw_circle(
        canvas.context,
        Point(point.x.pt, point.y.pt),
        CanvasUnit.from_px(13).pt
    )
    canvas.context.set_line_width(CanvasUnit.from_px(1).pt)
    canvas.context.set_source_rgba(*stroke)
    canvas.context.stroke()


draw_legend_circle(legend_r1_c1_sym, MilepostDrawer.mills_fill, MilepostDrawer.mills_stroke)
draw_legend_circle(legend_r1_c2_sym, MilepostDrawer.rowe_fill, MilepostDrawer.rowe_stroke)
draw_legend_circle(legend_r2_c1_sym, MilepostDrawer.mccoll_fill, MilepostDrawer.mccoll_stroke)
draw_legend_circle(legend_r2_c2_sym, MilepostDrawer.dudgeon_fill, MilepostDrawer.dudgeon_stroke)

canvas.close()
