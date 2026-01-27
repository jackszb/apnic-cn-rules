import requests
import json
import math
import subprocess
from pathlib import Path
import ipaddress
import sys

URL = "http://ftp.apnic.net/stats/apnic/delegated-apnic-latest"
RULES_DIR = Path("rules")
RULES_DIR.mkdir(parents=True, exist_ok=True)

def fetch_lines():
    try:
        r = requests.get(URL, timeout=30)
        r.raise_for_status()
        return r.text.splitlines()
    except Exception as e:
        print(f"获取 APNIC 数据失败: {e}")
        sys.exit(1)

def collapse_list(cidr_list):
    """单协议合并 IPv4 或 IPv6"""
    nets = [ipaddress.ip_network(c, strict=False) for c in cidr_list]
    merged = ipaddress.collapse_addresses(nets)
    return [str(n) for n in merged]

def write_json(file_name, cidrs):
    data = {"version": 3, "rules": [{"ip_cidr": cidrs}]}
    with open(RULES_DIR / file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_ipv4(lines):
    raw=[]
    for line in lines:
        if "|CN|ipv4" in line:
            parts=line.split("|")
            start_ip=parts[3]
            ip_count=int(parts[4])
            # 计算 CIDR
            cidr=32 - int(math.log2(ip_count))
            raw.append(f"{start_ip}/{cidr}")
    merged = collapse_list(raw)
    write_json("apnic_cn_ipv4.json", raw)       # 原始 IPv4
    return merged

def get_ipv6(lines):
    raw=[]
    for line in lines:
        if "|CN|ipv6" in line:
            parts=line.split("|")
            raw.append(f"{parts[3]}/{parts[4]}")
    merged = collapse_list(raw)
    write_json("apnic_cn_ipv6.json", raw)       # 原始 IPv6
    return merged

def compile_srs(json_name, srs_name):
    cmd=f"sing-box rule-set compile --output {RULES_DIR/srs_name} {RULES_DIR/json_name}"
    process=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line.strip())
    if process.wait()!=0:
        print(f"{srs_name} 编译失败")
        sys.exit(1)

if __name__=="__main__":
    lines=fetch_lines()

    ipv4_merged = get_ipv4(lines)
    ipv6_merged = get_ipv6(lines)

    # 合并 IPv4 + IPv6（直接拼接，避免 collapse IPv4+IPv6）
    merged = ipv4_merged + ipv6_merged
    write_json("apnic_cn_merged.json", merged)

    # 编译 SRS
    compile_srs("apnic_cn_ipv4.json","apnic_cn_ipv4.srs")
    compile_srs("apnic_cn_ipv6.json","apnic_cn_ipv6.srs")
    compile_srs("apnic_cn_merged.json","apnic_cn_merged.srs")

    print("规则生成完成，文件保存在 rules/ 文件夹")
