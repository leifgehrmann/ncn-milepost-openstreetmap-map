from pathlib import Path
import os
import urllib.request
import zipfile
import shutil

from map_engraver.canvas import CanvasBuilder
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
    shape_name = extract_name + '.shp'
    zip_path = cache_path.joinpath(zip_name)
    extract_path = cache_path.joinpath(extract_name)
    extract_shape_path = extract_path.joinpath(shape_name)
    shape_path = cache_path.joinpath(shape_name)

    # Check if Shapefile already exists. Skip if it does.
    if shape_path.exists():
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
    os.rename(extract_shape_path.as_posix(), shape_path.as_posix())

    # Delete ZIP and Extract.
    os.unlink(zip_path.as_posix())
    shutil.rmtree(extract_path.as_posix())


ne_root_url = 'https://www.naturalearthdata.com/' \
              'http//www.naturalearthdata.com/download/'
ne_land_url = ne_root_url + '10m/physical/ne_10m_land.zip'
ne_islands_url = ne_root_url + '10m/physical/ne_10m_minor_islands.zip'
ne_lakes_url = ne_root_url + '10m/physical/ne_10m_lakes.zip'
download_and_extract_shape(ne_land_url)
download_and_extract_shape(ne_islands_url)
download_and_extract_shape(ne_lakes_url)

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
