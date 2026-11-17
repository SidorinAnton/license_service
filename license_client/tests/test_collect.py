from src.collect import Device, _disk_serial, get_device_data


def test_get_device_data():
    license_key = "ABCD-1234-EFGH-B6B6"
    device = get_device_data("ABCD-1234-EFGH-B6B6")

    assert isinstance(device, Device)
    assert device.license_key == license_key
    assert device.cpu_cores > 0


def test_disk_serial_linux(mocker):
    mocker.patch("src.collect.platform.system", return_value="Linux")
    mock_subprocess = mocker.patch("src.collect.subprocess.check_output")
    mock_subprocess.return_value = "NAME SERIAL TYPE\nsda ABC123XYZ disk\n"

    assert _disk_serial() == "ABC123XYZ"


def test_disk_serial_windows(mocker):
    mocker.patch("src.collect.platform.system", return_value="Windows")
    mock_subprocess = mocker.patch("src.collect.subprocess.check_output")
    mock_subprocess.return_value = "WIN-SERIAL-999\n"

    assert _disk_serial() == "WIN-SERIAL-999"


def test_disk_serial_darwin(mocker):
    mocker.patch("src.collect.platform.system", return_value="Darwin")
    mock_subprocess = mocker.patch("src.collect.subprocess.check_output")

    mock_subprocess.return_value = '    "Serial Number" = "MAC-DISK-SERIAL-01";\n'
    assert _disk_serial() == "MAC-DISK-SERIAL-01"


def test_disk_serial_exception_handling(mocker):
    mocker.patch("src.collect.platform.system", return_value="Linux")
    mocker.patch("src.collect.subprocess.check_output", side_effect=Exception("Unexpected error"))

    assert _disk_serial() is None


def test_collect_device_data_exceptions(mocker):
    mocker.patch("src.collect.get_mac_address", side_effect=Exception("MAC error"))
    mocker.patch("src.collect.machineid.id", side_effect=Exception("Machine ID error"))
    mocker.patch("src.collect._disk_serial", return_value=None)

    device = get_device_data("ABCD-1234-EFGH-B6B6")
    assert device.mac_address is None
    assert device.machine_id is None
    assert device.disk_serial_number is None
