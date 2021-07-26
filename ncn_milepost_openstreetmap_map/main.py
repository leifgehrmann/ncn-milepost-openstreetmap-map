from pathlib import Path

from map_engraver.canvas import CanvasBuilder
from map_engraver.canvas.canvas_unit import CanvasUnit


# 1. Download Natural Earth shapefiles. In non-master GitHub Actions, use mock
#    coastline data.
# 2. Download OpenStreetMap milepost data. In GitHub Actions, use mock milepost
#    data.
# 3. Render the map (Later, create a dark-mode variant)
Path(__file__).parent.parent.joinpath('output/') \
    .mkdir(parents=True, exist_ok=True)
path = Path(__file__).parent.joinpath('../output/map.svg')
path.unlink(missing_ok=True)
canvas_builder = CanvasBuilder()
canvas_builder.set_path(path)
canvas_builder.set_size(CanvasUnit.from_mm(120), CanvasUnit.from_mm(185))
canvas = canvas_builder.build()
# 3.1 Land
# 3.2 Lakes
# 3.3 Milepost Symbols
# 3.4 Title and Labels
# 3.5 Margins
canvas.close()
