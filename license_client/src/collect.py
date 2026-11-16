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
    return Device(
        license_key=license_key,
        os_system=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        cpu_arch=platform.machine(),
        cpu_cores=os.cpu_count() or 0,
        mac_address=get_mac_address(),
        machine_id=machineid.id(),
        disk_serial_number=_disk_serial(),
    )


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

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return None
