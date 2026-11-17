import zlib


def calculate_checksum(parts: list[str]) -> str:
    base_str = "".join(parts[:3]).upper()
    # 1) calculate 32-bit checksum
    # 2) 0xFFFF -- 16-bit mask (0b1111_1111_1111_1111)
    # 3) crc & ffff = 16-bit crc
    crc = zlib.crc32(base_str.encode("utf-8")) & 0xFFFF
    # 4) 04X -- make crc in HEX (16-sys) and get 4 symbols
    return f"{crc:04X}"
