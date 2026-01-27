import requests
import math
import json
import subprocess
import ipaddress
import sys

URL = "http://ftp.apnic.net/stats/apnic/delegated-apnic-latest"


def fetch_apnic():
    try:
        r = requests.get(URL, timeout=30)
        r.raise_for_status()
        return r.text.splitlines()
    except Exception as e:
        print(f"APNIC 数据获取失败: {e}")
        sys.exit(1)


def merge_networks(cidr_list):
    nets = [ipaddress.ip_network(c, strict=False) for c in cidr_list]
    merged = ipaddress.collapse_addresses(nets)
    return [str(n) for n in merged]


def write_json(filename, cidrs):
    data = {
        "version": 3,
        "rules": [
            {
                "ip_cidr": cidrs
            }
        ]
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_china_ipv4(lines):
    raw = []
    for line in lines:
        if "|CN|ipv4" in line:
            parts = line.split("|")
            if len(parts) >= 5:
                start_ip = parts[3]
                ip_count = int(parts[4])
                cidr = 32 - ip_count.bit_length() + 1
                raw.append(f"{start_ip}/{cidr}")

    write_json("apnic_cn_ipv4.json", raw)
    merged = merge_networks(raw)
    write_json("apnic_cn_ipv4_merged.json", merged)


def get_china_ipv6(lines):
    raw = []
    for line in lines:
        if "|CN|ipv6" in line:
            parts = line.split("|")
            if len(parts) >= 5:
                raw.append(f"{parts[3]}/{parts[4]}")

    write_json("apnic_cn_ipv6.json", raw)
    merged = merge_networks(raw)
    write_json("apnic_cn_ipv6_merged.json", merged)


def compile_srs(name):
    cmd = f"sing-box rule-set compile --output {name}.srs {name}.json"
    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in p.stdout:
        print(line.strip())
    if p.wait() != 0:
        sys.exit(1)


if __name__ == "__main__":
    lines = fetch_apnic()

    get_china_ipv4(lines)
    get_china_ipv6(lines)

    compile_srs("apnic_cn_ipv4")
    compile_srs("apnic_cn_ipv6")
    compile_srs("apnic_cn_ipv4_merged")
    compile_srs("apnic_cn_ipv6_merged")
