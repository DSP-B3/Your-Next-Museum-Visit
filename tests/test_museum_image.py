from recommenders import RecSystem


def test_all_museum_have_image():
    rs = RecSystem()
    for museum in rs.all_museums:
        assert museum.image_url is not None
        assert museum.image_url.endswith(".jpg")
        assert museum.image_url.startswith("/static/museum_images/")
