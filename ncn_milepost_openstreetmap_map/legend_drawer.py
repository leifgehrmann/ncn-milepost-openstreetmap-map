from map_engraver.canvas.canvas_unit import CanvasUnit
from map_engraver.data.pango.layout import Layout
from map_engraver.drawable.text.pango_drawer import PangoDrawer
from map_engraver.graphicshelper import CairoHelper
from pangocffi import FontDescription
from shapely.geometry import Point
from typing import Tuple

from map_engraver.canvas import Canvas
from map_engraver.canvas.canvas_coordinate import CanvasCoordinate

from ncn_milepost_openstreetmap_map.milepost_drawer import MilepostDrawer


class LegendDrawer:
    def __init__(
            self,
            font: FontDescription,
            text_color: Tuple[float, float, float, float],
            position: CanvasCoordinate
    ):
        self.font = font
        self.text_color = text_color
        self.position = position
        pass

    @staticmethod
    def draw_legend_circle(
            canvas: Canvas,
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

    def draw(self, canvas: Canvas):
        r1c1 = Layout(canvas)
        r1c1.pango_layout.set_font_description(self.font)
        r1c1.set_text('Mills')
        r1c1.color = self.text_color
        r1c2 = Layout(canvas)
        r1c2.pango_layout.set_font_description(self.font)
        r1c2.set_text('Rowe')
        r1c2.color = self.text_color
        r2c1 = Layout(canvas)
        r2c1.pango_layout.set_font_description(self.font)
        r2c1.set_text('McColl')
        r2c1.color = self.text_color
        r2c2 = Layout(canvas)
        r2c2.pango_layout.set_font_description(self.font)
        r2c2.set_text('Dudgeon')
        r2c2.color = self.text_color

        c1_x = self.position.x
        c2_x = c1_x + CanvasUnit.from_px(100)

        r1_y = self.position.y
        r2_y = r1_y + CanvasUnit.from_px(12 + 20)

        sym_width = CanvasUnit.from_px(12)
        sym_radius = sym_width / 2
        text_height = r1c1.logical_extents.height
        text_mid = text_height / 2.5

        r1c1_sym = CanvasCoordinate(c1_x + sym_radius, r1_y + text_mid)
        r1c2_sym = CanvasCoordinate(c2_x + sym_radius, r1_y + text_mid)
        r2c1_sym = CanvasCoordinate(c1_x + sym_radius, r2_y + text_mid)
        r2c2_sym = CanvasCoordinate(c2_x + sym_radius, r2_y + text_mid)
        r1c1.position = CanvasCoordinate(r1c1_sym.x + sym_width, r1_y)
        r1c2.position = CanvasCoordinate(r1c2_sym.x + sym_width, r1_y)
        r2c1.position = CanvasCoordinate(r2c1_sym.x + sym_width, r2_y)
        r2c2.position = CanvasCoordinate(r2c2_sym.x + sym_width, r2_y)

        text_drawer = PangoDrawer()
        text_drawer.pango_objects = [
            r1c1,
            r1c2,
            r2c1,
            r2c2
        ]
        text_drawer.draw(canvas)

        self.draw_legend_circle(
            canvas,
            r1c1_sym,
            MilepostDrawer.mills_fill,
            MilepostDrawer.mills_stroke
        )
        self.draw_legend_circle(
            canvas,
            r1c2_sym,
            MilepostDrawer.rowe_fill,
            MilepostDrawer.rowe_stroke
        )
        self.draw_legend_circle(
            canvas,
            r2c1_sym,
            MilepostDrawer.mccoll_fill,
            MilepostDrawer.mccoll_stroke
        )
        self.draw_legend_circle(
            canvas,
            r2c2_sym,
            MilepostDrawer.dudgeon_fill,
            MilepostDrawer.dudgeon_stroke
        )
