"""Bounded public-web crawler. DNS addresses are validated and pinned per request."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import trafilatura

AGENT = "HoaksCheckBot"
MAX_BYTES = 8_000_000

def validate_url(url):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("Gunakan URL HTTP/HTTPS publik tanpa kredensial.")
    if p.port not in {None, 80, 443}:
        raise ValueError("Hanya port 80 dan 443 yang diizinkan.")
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Alamat lokal, privat, dan jaringan internal tidak diizinkan.")
    return p, addresses[0][4][0]

def fetch(url, allowed=None):
    for _ in range(5):
        if allowed and not allowed(url):
            raise ValueError("URL dilarang robots.txt.")
        p, address = validate_url(url)
        port = p.port or (443 if p.scheme == "https" else 80)
        conn = http.client.HTTPConnection(p.hostname, port, timeout=12)
        sock = socket.create_connection((address, port), timeout=12)
        try:
            if p.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=p.hostname)
            conn.sock = sock
            conn.request("GET", urlunsplit(("", "", p.path or "/", p.query, "")), headers={"User-Agent": AGENT, "Accept-Encoding": "identity"})
            response = conn.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirect tanpa tujuan.")
                target = urljoin(url, location)
                if urlsplit(target).hostname != p.hostname:
                    raise ValueError("Redirect lintas hostname tidak diikuti; masukkan URL tujuan langsung.")
                url = target
                continue
            if response.status >= 400:
                return url, response.status, ""
            content_type = response.getheader("Content-Type", "").lower()
            if not any(t in content_type for t in ("text/", "application/xhtml+xml")):
                raise ValueError("Respons bukan dokumen teks/HTML.")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Halaman melebihi batas 8 MB; tidak dibaca sebagian.")
            return url, response.status, data.decode("utf-8", errors="replace")
        finally:
            conn.close()
            sock.close()
    raise ValueError("Terlalu banyak redirect.")

def crawl(seed, max_pages=1):
    parsed, _ = validate_url(seed)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    _, status, robots_text = fetch(origin + "/robots.txt")
    if status not in {200, 404}:
        raise ValueError("robots.txt tidak dapat diverifikasi; crawling dihentikan.")
    robots = RobotFileParser()
    robots.parse(robots_text.splitlines() if status == 200 else [])
    delay = max(1, robots.crawl_delay(AGENT) or 1)
    if delay > 10:
        raise ValueError("Situs meminta crawl-delay di atas 10 detik; gunakan input teks.")
    queue, visited, articles, errors = [seed], set(), [], []
    while queue and len(visited) < max_pages:
        url = queue.pop(0).split("#")[0]
        if url in visited:
            continue
        visited.add(url)
        if not robots.can_fetch(AGENT, url):
            errors.append({"url": url, "error": "Dilarang oleh robots.txt."})
            continue
        time.sleep(delay)
        try:
            final, status, html = fetch(url, lambda target: robots.can_fetch(AGENT, target))
            if status != 200:
                raise ValueError(f"Situs mengembalikan HTTP {status}.")
            if not robots.can_fetch(AGENT, final):
                raise ValueError("URL akhir dilarang robots.txt.")
            soup = BeautifulSoup(html, "html.parser")
            body = trafilatura.extract(html, include_comments=False, include_tables=True)
            if body and len(body.strip()) >= 100:
                articles.append({"url": final, "title": soup.title.get_text(strip=True) if soup.title else final, "text": body, "extraction_truncated": False})
            else:
                errors.append({"url": url, "error": "Teks artikel terlalu sedikit; halaman mungkin membutuhkan JavaScript."})
            for link in soup.select("a[href]")[:200]:
                target = urljoin(final, link["href"]).split("#")[0]
                q = urlsplit(target)
                if q.scheme in {"https", "http"} and q.netloc == parsed.netloc and target not in visited and target not in queue and len(queue) < 100:
                    queue.append(target)
        except (ValueError, OSError, http.client.HTTPException) as exc:
            errors.append({"url": url, "error": str(exc)})
    return articles, errors
