#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BPB Panel 4.0 subscription (JSON config array) -> v2ray share links (vless://, trojan://)
- Input: URL that returns JSON, or a local JSON file
- Output: raw links (one per line) or Base64 subscription
No third-party deps (stdlib only).
"""

import argparse
import base64
import json
import sys
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

SKIP_PROTOCOLS = {"dns", "freedom", "blackhole"}
ALLOW_PROTOCOLS = {"vless", "trojan"}  # 可按需扩展：vmess, shadowsocks...

def b64_utf8(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

def url_fetch_text(url: str, timeout: int = 15) -> str:
    req = Request(url, headers={"User-Agent": "bpb4-to-v2ray/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")

def norm_host_for_url(host: str) -> str:
    """Ensure IPv6 is bracketed in URL. Keep existing brackets if present."""
    if not host:
        return host
    h = host.strip()
    if h.startswith("[") and h.endswith("]"):
        return h
    # If contains ':' assume ipv6 literal (not domain)
    if ":" in h and not h.startswith("["):
        return f"[{h}]"
    return h

def get_stream_params(stream: dict) -> dict:
    """Extract common params from Xray streamSettings to share-link query params."""
    params = {}
    if not isinstance(stream, dict):
        return params

    network = stream.get("network")
    security = stream.get("security")

    # TLS
    if security == "tls":
        params["security"] = "tls"
        tls = stream.get("tlsSettings") or {}
        sni = tls.get("serverName")
        fp = tls.get("fingerprint")
        alpn = tls.get("alpn")
        allow_insecure = tls.get("allowInsecure")

        if sni:
            params["sni"] = sni
        if fp:
            params["fp"] = fp
        if isinstance(alpn, list) and alpn:
            params["alpn"] = ",".join(alpn)
        if isinstance(allow_insecure, bool):
            params["allowInsecure"] = "1" if allow_insecure else "0"

    # WS
    if network == "ws":
        params["type"] = "ws"
        ws = stream.get("wsSettings") or {}
        host = ws.get("host")
        path = ws.get("path")
        if host:
            params["host"] = host
        if path:
            # path 建议编码，避免 ?&= 等影响 query 解析
            params["path"] = path

    # 你也可以在这里扩展 grpc/httpupgrade/reality 等
    return params

def build_vless_link(ob: dict, fallback_name: str) -> str | None:
    settings = ob.get("settings") or {}
    vnext_list = settings.get("vnext") or []
    if not vnext_list:
        return None
    v = vnext_list[0]
    addr = norm_host_for_url(str(v.get("address", "")).strip())
    port = v.get("port")
    users = v.get("users") or []
    if not users:
        return None
    u = users[0]
    uuid = u.get("id")
    enc = u.get("encryption", "none")
    flow = u.get("flow")

    if not addr or not port or not uuid:
        return None

    params = {"encryption": enc}
    if flow:
        params["flow"] = flow

    params.update(get_stream_params(ob.get("streamSettings") or {}))

    # urlencode 会编码特殊字符；path 内部也会被编码，通常 v2rayN 可正常识别
    query = urlencode(params, doseq=False, safe="")
    name = quote(ob.get("tag") or fallback_name or "bpb", safe="")
    return f"vless://{uuid}@{addr}:{port}?{query}#{name}"

def build_trojan_link(ob: dict, fallback_name: str) -> str | None:
    settings = ob.get("settings") or {}
    servers = settings.get("servers") or []
    if not servers:
        return None
    s = servers[0]
    addr = norm_host_for_url(str(s.get("address", "")).strip())
    port = s.get("port")
    password = s.get("password")

    if not addr or not port or not password:
        return None

    params = {}
    params.update(get_stream_params(ob.get("streamSettings") or {}))

    query = urlencode(params, doseq=False, safe="")
    name = quote(ob.get("tag") or fallback_name or "bpb", safe="")
    # trojan://password@host:port?...
    return f"trojan://{quote(str(password), safe='')}@{addr}:{port}?{query}#{name}"

def extract_links_from_item(item: dict) -> list[str]:
    links = []
    if not isinstance(item, dict):
        return links

    fallback_name = item.get("remarks") or "bpb"
    outbounds = item.get("outbounds") or []
    for ob in outbounds:
        if not isinstance(ob, dict):
            continue
        proto = ob.get("protocol")
        if proto in SKIP_PROTOCOLS:
            continue
        if proto not in ALLOW_PROTOCOLS:
            continue

        if proto == "vless":
            link = build_vless_link(ob, fallback_name)
        elif proto == "trojan":
            link = build_trojan_link(ob, fallback_name)
        else:
            link = None

        if link:
            links.append(link)
    return links

def main():
    ap = argparse.ArgumentParser(description="Convert BPB Panel 4.0 JSON subscription to v2ray share links")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="BPB subscription URL that returns JSON")
    g.add_argument("--infile", help="Local JSON file path")
    ap.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds (default: 15)")
    ap.add_argument("--format", choices=["raw", "base64"], default="base64", help="Output format")
    ap.add_argument("--out", help="Write output to file (default: stdout)")
    args = ap.parse_args()

    if args.url:
        raw = url_fetch_text(args.url, timeout=args.timeout)
    else:
        with open(args.infile, "r", encoding="utf-8") as f:
            raw = f.read()

    data = json.loads(raw)
    items = data if isinstance(data, list) else [data]

    all_links = []
    for it in items:
        all_links.extend(extract_links_from_item(it))

    # 去重但保序
    seen = set()
    uniq = []
    for x in all_links:
        if x not in seen:
            uniq.append(x)
            seen.add(x)

    if not uniq:
        raise SystemExit("No vless/trojan links extracted. Check your JSON structure or extend ALLOW_PROTOCOLS.")

    text = "\n".join(uniq) + "\n"
    if args.format == "base64":
        out_text = b64_utf8(text)
    else:
        out_text = text

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text)
    else:
        sys.stdout.write(out_text)

if __name__ == "__main__":
    main()
