from map_engraver.canvas import Canvas
from map_engraver.data.osm import Osm
from map_engraver.graphicshelper import CairoHelper
from shapely.geometry import Point
from typing import Tuple, Optional

from map_engraver.canvas.canvas_unit import CanvasUnit
from map_engraver.drawable.geometry.symbol_drawer import SymbolDrawer


class MilepostDrawer(SymbolDrawer):
    mills_fill = (255/255, 66/255, 0/255, 1)
    mills_stroke = (0.0, 0.0, 0.0, 1)
    rowe_fill = (88/255, 181/255, 61/255, 1)
    rowe_stroke = (0.0, 0.0, 0.0, 1)
    mccoll_fill = (95/255, 228/255, 255/255, 1)
    mccoll_stroke = (0.0, 0.0, 0.0, 1)
    dudgeon_fill = (255/255, 240/255, 32/255, 1)
    dudgeon_stroke = (0.0, 0.0, 0.0, 1)

    def __init__(self, osm_map: Osm):
        super().__init__()
        self.size = CanvasUnit.from_px(10).pt
        self.osm_map = osm_map

    def get_colors(self, osm_ref: str) -> Tuple[
        Optional[Tuple[float, float, float, float]],
        Optional[Tuple[float, float, float, float]]
    ]:
        node = self.osm_map.get_node(osm_ref)
        if 'ncn_milepost' not in node.tags:
            return None, None
        if node.tags['ncn_milepost'] == 'mills':  # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 = Red
            return (
                MilepostDrawer.mills_fill,
                MilepostDrawer.mills_stroke
            )
        if node.tags['ncn_milepost'] == 'rowe':  # 🏴󠁧󠁢󠁷󠁬󠁳󠁿 = Green
            return (
                MilepostDrawer.rowe_fill,
                MilepostDrawer.rowe_stroke
            )
        if node.tags['ncn_milepost'] == 'mccoll':  # 🏴󠁧󠁢󠁳󠁣󠁴󠁿 = Blue
            return (
                MilepostDrawer.mccoll_fill,
                MilepostDrawer.mccoll_stroke
            )
        if node.tags['ncn_milepost'] == 'dudgeon':  # Ireland = Yellow
            return (
                MilepostDrawer.dudgeon_fill,
                MilepostDrawer.dudgeon_stroke
            )
        return None, None

    def draw_symbol(self, ref: str, point: Point, canvas: Canvas):
        fill, stroke = self.get_colors(ref)
        if fill is None:
            return

        canvas.context.set_source_rgba(*fill)
        CairoHelper.draw_circle(
            canvas.context,
            point,
            CanvasUnit.from_px(6).pt
        )
        canvas.context.fill_preserve()
        canvas.context.set_line_width(CanvasUnit.from_px(0.75).pt)
        canvas.context.set_source_rgba(*stroke)
        canvas.context.stroke()
