# ncn-milepost-openstreetmap-map

Generates a map of National Cycle Network mileposts using data from
OpenStreetMap, rendered using [Map-engraver].

## Output

| Light mode | Dark mode |
|-|-|
| ![A map of Millennium Mileposts in the United Kingdom, by Type. (Light variant)](http://ncn-milepost-openstreetmap-map.leifgehrmann.com/map-light.svg) | ![A map of Millennium Mileposts in the United Kingdom, by Type. (Dark variant)](http://ncn-milepost-openstreetmap-map.leifgehrmann.com/map-dark.svg) |

Millennium Milepost data: © OpenStreetMap contributors ([Overpass query]);
Coastline and lake data: [NaturalEarthData.com];

[Map-engraver]: https://github.com/leifgehrmann/map-engraver
[Overpass query]: https://overpass-turbo.eu/s/HMg
[NaturalEarthData.com]: https://www.naturalearthdata.com/downloads/10m-physical-vectors/

## How to run

```shell
make install
make main
```
