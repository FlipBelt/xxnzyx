"""Validate the repository's domain routing in an isolated local Nginx container."""
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

repo = Path(__file__).resolve().parents[1]
scratch = repo.parent / "nginx-smoke"
scratch.mkdir(exist_ok=True)
site = scratch / "site"
(site / "admin" / "assets").mkdir(parents=True, exist_ok=True)
(site / "participant-domain-h5").mkdir(parents=True, exist_ok=True)
(site / "admin" / "index.html").write_text("<title>ADMIN-FIXTURE</title>", encoding="utf-8")
(site / "admin" / "assets" / "probe.js").write_text("/* ADMIN-ASSET */", encoding="utf-8")
(site / "participant-domain-h5" / "index.html").write_text("<title>PARTICIPANT-FIXTURE</title>", encoding="utf-8")
source = (repo / "deploy" / "nzyx.flipbeltchina.com.conf").read_text(encoding="utf-8")
# Only the TLS listener/certificate directives are replaced in this local copy.
# Every location and its ordering comes unchanged from the actual deployment file.
start = source.index("server {", source.index("server {") + 1)
local = source[start:]
local = re.sub(r"listen 443 ssl http2;", "listen 80;", local)
local = re.sub(r"listen \[::\]:443 ssl http2;", "listen [::]:80;", local)
local = re.sub(r"^\s*(ssl_certificate|ssl_certificate_key|ssl_dhparam|include /etc/letsencrypt/).*?;\s*$", "", local, flags=re.M)
config = scratch / "default.conf"
config.write_text(local, encoding="utf-8")
name = "xxnzyx-route-test-" + uuid4().hex[:10]


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=60)
    return result.stdout.strip()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


opener = build_opener(NoRedirect())


def get(origin: str, route: str, *, wechat: bool = False) -> tuple[int, str, object]:
    headers = {"Host": "nzyx.flipbeltchina.com"}
    if wechat:
        headers["User-Agent"] = "MicroMessenger"
    request = Request(origin + route, headers=headers)
    try:
        response = opener.open(request, timeout=5)
    except HTTPError as exc:
        response = exc
    with response:
        return response.status, response.read().decode(), response.headers


try:
    docker(
        "run", "--detach", "--rm", "--name", name, "-p", "127.0.0.1::80",
        "--mount", f"type=bind,source={config},target=/etc/nginx/conf.d/default.conf,readonly",
        "--mount", f"type=bind,source={site},target=/srv/flipbelt-challenge,readonly", "nginx:alpine",
    )
    validation = subprocess.run(["docker", "exec", name, "nginx", "-t"], capture_output=True, text=True, timeout=30)
    assert validation.returncode == 0, validation.stderr
    port = docker("port", name, "80/tcp").rsplit(":", 1)[1]
    origin = "http://127.0.0.1:" + port
    for _attempt in range(30):
        try:
            get(origin, "/")
            break
        except (URLError, TimeoutError):
            time.sleep(.1)
    for route in ("/flipbelt-admin/", "/flipbelt-admin/deep-link"):
        status, body, headers = get(origin, route)
        assert status == 200 and "ADMIN-FIXTURE" in body and "PARTICIPANT" not in body, (route, status, body)
        assert "no-store" in headers["Cache-Control"]
    status, body, headers = get(origin, "/flipbelt-admin/assets/probe.js")
    assert status == 200 and "ADMIN-ASSET" in body
    assert "javascript" in headers["Content-Type"] and "immutable" in headers["Cache-Control"]
    assert get(origin, "/flipbelt-admin/assets/missing.js")[0] == 404
    status, _, headers = get(origin, "/flipbelt-admin")
    assert status == 301 and headers["Location"].endswith("/flipbelt-admin/")
    status, body, _ = get(origin, "/")
    assert status == 200 and "PARTICIPANT-FIXTURE" in body
    for route in ("/", "/wx-entry-20260904", "/wx-entry-20260909"):
        status, _, headers = get(origin, route, wechat=True)
        assert status == 302 and headers["Location"].endswith("/wx-entry-20261106")
        assert "no-store" in headers["Cache-Control"]
    status, body, headers = get(origin, "/wx-entry-20261106", wechat=True)
    assert status == 200 and "PARTICIPANT-FIXTURE" in body
    assert "no-store" in headers["Cache-Control"]
    print("Nginx -t and 10 domain routing/cache checks passed; local fixtures only")
finally:
    subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=30)
