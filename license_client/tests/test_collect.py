from src.collect import Device, get_device_data


def test_get_device_data():
    license_key = "ABCD-1234-EFGH-B6B6"
    device = get_device_data("ABCD-1234-EFGH-B6B6")

    assert isinstance(device, Device)
    assert device.license_key == license_key
    assert device.cpu_cores > 0
