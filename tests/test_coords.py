from recommenders import get_city_coordinates


def test_get_city_coordinates():

    # Known coordinates of some cities, verified with a search engine.
    cities = {
        "ABCOUDE": (52.2721, 4.9705),
        "BUNNIK": (52.0665, 5.2008),
        "Capelle aan den IJssel": (51.935, 4.5894),
    }

    for city, coordinates in cities.items():
        lat1, lon1 = get_city_coordinates(city)
        lat2, lon2 = coordinates

        # The coordinates should be within 0.02 degrees of the known coordinates.
        # This is about 2 km, which is a reasonable margin of error for this purpose.
        assert abs(lat1 - lat2) < 0.02
        assert abs(lon1 - lon2) < 0.02
