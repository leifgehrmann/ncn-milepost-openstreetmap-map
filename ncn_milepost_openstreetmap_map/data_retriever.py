from pathlib import Path
import shutil
import os
import zipfile
import urllib.parse
import urllib.request
from urllib.error import HTTPError


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
    attempts = 0
    while attempts < 5:
        try:
            data = urllib.request.urlopen(url)
            data = data.read()
            file = open(zip_path.as_posix(), 'wb')
            file.write(data)
            file.close()
            break
        except HTTPError as e:
            if attempts == 4:
                raise e
            attempts += 1

    # Extract the ZIP within the cache.
    with zipfile.ZipFile(zip_path.as_posix()) as zf:
        zf.extractall(extract_path.as_posix())

    # Move Shapefile out of the extract directory to the cache directory.
    os.rename(extract_shp_path.as_posix(), shp_path.as_posix())
    os.rename(extract_dbf_path.as_posix(), dbf_path.as_posix())

    # Delete ZIP and Extract.
    os.unlink(zip_path.as_posix())
    shutil.rmtree(extract_path.as_posix())


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
