import os
import platform
from dataclasses import dataclass

import machineid
from getmac import get_mac_address


@dataclass
class Device:
    license_key: str
    os_system: str
    os_release: str
    os_version: str
    cpu_arch: str
    cpu_cores: int
    mac_address: str | None
    machine_id: str


def get_device_data(license_key: str) -> Device:
    return Device(
        license_key=license_key,
        os_system=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        cpu_arch=platform.machine(),
        cpu_cores=os.cpu_count() or 0,
        mac_address=get_mac_address(),
        machine_id=machineid.id(),
    )
