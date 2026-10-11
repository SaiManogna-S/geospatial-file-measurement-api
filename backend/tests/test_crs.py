from shapely.geometry import box

from app.services.crs import choose_measurement_crs, utm_crs


def test_utm_zone_northern_hemisphere():
    crs = utm_crs(12.0, 48.0)
    assert crs.to_epsg() == 32633


def test_utm_zone_southern_hemisphere():
    crs = utm_crs(18.4, -33.9)
    assert crs.to_epsg() == 32734


def test_local_extent_uses_utm():
    geom = box(12.0, 48.0, 12.2, 48.15)
    selected = choose_measurement_crs([geom])
    assert selected.crs.to_epsg() == 32633
    assert "UTM" in selected.strategy or "utm" in selected.strategy.lower() or "Local UTM" in selected.strategy


def test_broad_extent_uses_laea():
    geom = box(-20.0, 10.0, 40.0, 50.0)
    selected = choose_measurement_crs([geom])
    assert selected.crs.to_epsg() is None
    assert "Equal Area" in selected.strategy
