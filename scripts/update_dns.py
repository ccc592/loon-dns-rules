"""Build a Host-only Loon plugin from the complete upstream CN domain list.

No credentials, application configuration, or third-party Python packages needed.
Unknown syntax or an unexpectedly small list fails before replacing any output.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "MetaCubeX/meta-rules-dat"
SOURCE_PATH = "geo/geosite/cn.list"
ALI = "https://223.5.5.5/dns-query"


def get(url):
    headers = {"User-Agent": "loon-dns-rules-generator"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if url.startswith("https://api.github.com/") and token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000:
        raise ValueError("Upstream source is unexpectedly large")
    return data


def parse(data):
    domains = set()
    for line in data.decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("+."):
            raise ValueError("Unsupported upstream matcher; keeping previous plugin")
        domain = line[2:].lower()
        if not re.fullmatch(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)*", domain):
            raise ValueError("Invalid domain in source")
        domains.add(domain)
    if not 50_000 <= len(domains) <= 300_000:
        raise ValueError("CN domain count outside expected range")
    return domains


def covered(domain, suffixes):
    parts = domain.split(".")
    return any(".".join(parts[i:]) in suffixes for i in range(len(parts)))


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w", encoding="utf-8", newline="\n") as handle:
        temporary = Path(handle.name)
        handle.write(content)
    os.replace(temporary, path)


def build(data, revision):
    domains = parse(data)
    source_count = len(domains)
    exceptions = {line.strip() for line in (ROOT / 'foreign-dns-exceptions.txt').read_text().splitlines()
                  if line.strip() and not line.startswith('#')}
    # Explicit foreign DNS exceptions are independent of upstream CN changes.
    domains = {d for d in domains if not covered(d, exceptions)}
    if any(covered(d, domains) for d in exceptions):
        raise ValueError('A broader CN suffix conflicts with a foreign DNS exception')
    old = ROOT / "manifest.json"
    if old.exists():
        previous_count = json.loads(old.read_text())["cn_suffix_count"]
        if len(domains) < previous_count * 0.9:
            raise ValueError("Source shrank by more than 10%; manual investigation required")
    samples_cn = ["baidu.com", "www.baidu.com", "qq.com", "www.taobao.com",
                  "www.bilibili.com", "www.jd.com", "www.douyin.com", "www.gov.cn"]
    samples_foreign = ["chatgpt.com", "api.openai.com", "claude.ai", "claude.com",
                       "gemini.google.com", "generativelanguage.googleapis.com",
                       "www.google.com", "browserleaks.com", "api4.ipify.org"]
    if not all(covered(d, domains) for d in samples_cn):
        raise ValueError("Domestic classification regression")
    if any(covered(d, domains) for d in samples_foreign):
        raise ValueError("Foreign/AI domain unexpectedly classified as domestic")
    lines = ["#!name = 国内域名 AliDNS 加密解析（完整 CN）",
             "#!desc = 完整 CN 域名使用阿里 DoH；其他域名沿用主配置 DNS。只含 Host，不修改规则或插件。",
             "#!author = ccc592",
             "#!homepage = https://github.com/ccc592/loon-dns-rules",
             "#!date = " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
             "# Source: https://github.com/" + UPSTREAM,
             "# Source revision: " + revision,
             "# License: GPL-3.0; see LICENSE and README.md for attribution.",
             "", "[Host]"]
    for domain in sorted(domains):
        lines.extend([domain + " = server:" + ALI, "*." + domain + " = server:" + ALI])
    plugin = "\n".join(lines) + "\n"
    if re.findall(r"^\[([^\]]+)\]$", plugin, re.M) != ["Host"]:
        raise ValueError("Unexpected plugin section")
    manifest = {"upstream_repository": UPSTREAM, "upstream_revision": revision,
                "upstream_path": SOURCE_PATH,
                "source_sha256": hashlib.sha256(data).hexdigest(),
                "source_cn_suffix_count": source_count,
                "excluded_cn_suffix_count": source_count - len(domains),
                "cn_suffix_count": len(domains), "host_mapping_count": len(domains) * 2,
                "plugin_sha256": hashlib.sha256(plugin.encode()).hexdigest(),
                "plugin_size_bytes": len(plugin.encode()),
                "domestic_samples_checked": samples_cn,
                "foreign_samples_checked": samples_foreign}
    atomic_write(ROOT / "plugins/China-DNS.lpx", plugin)
    atomic_write(old, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ["upstream_revision", "cn_suffix_count", "host_mapping_count", "plugin_sha256"]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    if args.source_file:
        if not args.revision:
            parser.error("--source-file requires --revision")
        revision = args.revision
        data = args.source_file.read_bytes()
    else:
        revision = json.loads(get("https://api.github.com/repos/" + UPSTREAM + "/commits/meta"))["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Invalid upstream revision")
        data = get("https://raw.githubusercontent.com/" + UPSTREAM + "/" + revision + "/" + SOURCE_PATH)
    build(data, revision)


if __name__ == "__main__":
    main()
