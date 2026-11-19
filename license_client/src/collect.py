import hashlib
import os
import platform
import subprocess
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
    machine_id: str | None
    disk_serial_number: str | None


def get_device_data(license_key: str) -> Device:
    try:
        mac_address = get_mac_address()
    except:  # noqa E722
        mac_address = None

    try:
        machine_id = machineid.id()
    except:  # noqa E722
        machine_id = None

    return Device(
        license_key=license_key,
        os_system=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        cpu_arch=platform.machine(),
        cpu_cores=os.cpu_count() or 0,
        mac_address=mac_address,
        machine_id=machine_id,
        disk_serial_number=_disk_serial(),
    )


def calculate_device_fingerprint(device_data: Device) -> str:
    def _normalization(val) -> str:
        if val is None:
            return "none"
        s = str(val).strip()
        return s if s else "none"

    raw_str = "|".join(
        [
            "v1-weak",
            f"os_system={_normalization(device_data.os_system)}",
            f"os_version={_normalization(device_data.os_version)}",
            f"os_release={_normalization(device_data.os_release)}",
            f"cpu_arch={_normalization(device_data.cpu_arch)}",
            f"cpu_cores={_normalization(device_data.cpu_cores)}",
            f"mac={_normalization(device_data.mac_address)}",
        ]
    )
    if device_data.machine_id or device_data.disk_serial_number:
        raw_str = "|".join(
            [
                "v1",
                f"machine_id={_normalization(device_data.machine_id)}",
                f"disk_serial={_normalization(device_data.disk_serial_number)}",
            ]
        )
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def _disk_serial() -> str | None:
    system = platform.system()
    try:
        if system == "Linux":
            out = subprocess.check_output(["lsblk", "-d", "-no", "NAME,SERIAL,TYPE"], text=True)

            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] == "disk" and parts[1] != "":
                    return parts[1]
            return None

        if system == "Windows":
            out = subprocess.check_output(
                [
                    "powershell",
                    "-Command",
                    "Get-CimInstance Win32_DiskDrive | Select-Object -First 1 -ExpandProperty SerialNumber",
                ],
                text=True,
            )
            s = out.strip()
            return s if s else None

        if system == "Darwin":
            out = subprocess.check_output(["ioreg", "-rd1", "-w0", "-c", "AppleANS2Controller"], text=True)
            for line in out.splitlines():
                if '"Serial Number"' in line:
                    return line.split('"')[-2].strip()

            out = subprocess.check_output(["ioreg", "-rd1", "-w0", "-c", "AppleAHCIDiskDriver"], text=True)
            for line in out.splitlines():
                if '"Serial Number"' in line:
                    return line.split('"')[-2].strip()
            return None

    except:  # noqa E722
        return None
    return None
