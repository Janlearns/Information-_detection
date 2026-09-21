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
MAX_REDIRECTS = 5
TRANSIENT_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


def _parse_url(url):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError("Gunakan URL HTTP/HTTPS publik tanpa kredensial.")
    if p.port not in {None, 80, 443}:
        raise ValueError("Hanya port 80 dan 443 yang diizinkan.")
    return p


def validate_url(url):
    p = _parse_url(url)
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Alamat lokal, privat, dan jaringan internal tidak diizinkan.")
    return p, addresses[0][4][0]


def _canonical_host(hostname):
    return hostname[4:] if hostname.startswith("www.") else hostname


def _check_redirect(source, target):
    previous, following = _parse_url(source), _parse_url(target)
    if _canonical_host(previous.hostname) != _canonical_host(following.hostname):
        raise ValueError("Redirect ke domain lain tidak diikuti; masukkan URL tujuan langsung.")
    if previous.scheme == "https" and following.scheme != "https":
        raise ValueError("Redirect dari HTTPS ke HTTP tidak diikuti.")


class _HTTPStatusError(ValueError):
    def __init__(self, message, status):
        super().__init__(message)
        self.retryable = status in TRANSIENT_HTTP_STATUSES


def is_retryable_error(exc):
    """Retry temporary transport/HTTP failures, never TLS or access denials."""
    if isinstance(exc, ssl.SSLError):
        return False
    return bool(getattr(exc, "retryable", False)) or isinstance(
        exc, (TimeoutError, ConnectionResetError, ConnectionAbortedError, http.client.RemoteDisconnected)
    )


def fetch(url, allowed=None):
    visited = set()
    for _ in range(MAX_REDIRECTS + 1):
        url = url.split("#", 1)[0]
        if url in visited:
            raise ValueError("Redirect berulang terdeteksi.")
        visited.add(url)
        if allowed and not allowed(url):
            raise ValueError("URL dilarang robots.txt.")
        p, address = validate_url(url)
        port = p.port or (443 if p.scheme == "https" else 80)
        conn = http.client.HTTPConnection(p.hostname, port, timeout=12)
        sock = None
        try:
            sock = socket.create_connection((address, port), timeout=12)
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
                _check_redirect(url, target)
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
            if sock is not None:
                sock.close()
    raise ValueError("Terlalu banyak redirect.")


class _RobotsPolicies:
    """Cache rules per origin, including a redirect's new host or scheme."""
    def __init__(self):
        self.policies = {}

    def for_url(self, url):
        parsed = _parse_url(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self.policies:
            _, status, robots_text = fetch(origin + "/robots.txt")
            if status not in {200, 404}:
                raise _HTTPStatusError(
                    f"robots.txt di {origin} mengembalikan HTTP {status}; crawling dihentikan.", status
                )
            robots = RobotFileParser()
            robots.parse(robots_text.splitlines() if status == 200 else [])
            delay = max(1, robots.crawl_delay(AGENT) or 1)
            if delay > 10:
                raise ValueError("Situs meminta crawl-delay di atas 10 detik; gunakan input teks.")
            self.policies[origin] = robots, delay
        return self.policies[origin]

    def allows(self, url, wait=False):
        robots, delay = self.for_url(url)
        if not robots.can_fetch(AGENT, url):
            return False
        if wait:
            time.sleep(delay)
        return True


def crawl(seed, max_pages=1):
    validate_url(seed)
    policies = _RobotsPolicies()
    policies.for_url(seed)
    queue, visited, articles, errors = [seed], set(), [], []
    while queue and len(visited) < max_pages:
        url = queue.pop(0).split("#")[0]
        if url in visited:
            continue
        visited.add(url)
        try:
            final, status, html = fetch(url, lambda target: policies.allows(target, wait=True))
            if status != 200:
                raise _HTTPStatusError(f"Situs mengembalikan HTTP {status}.", status)
            if not policies.allows(final):
                raise ValueError("URL akhir dilarang robots.txt.")
            soup = BeautifulSoup(html, "html.parser")
            body = trafilatura.extract(html, include_comments=False, include_tables=True)
            if body and len(body.strip()) >= 100:
                articles.append({"url": final, "title": soup.title.get_text(strip=True) if soup.title else final, "text": body, "extraction_truncated": False})
            else:
                errors.append({"url": url, "error": "Teks artikel terlalu sedikit; halaman mungkin membutuhkan JavaScript.", "retryable": False})
            for link in soup.select("a[href]")[:200]:
                target = urljoin(final, link["href"]).split("#")[0]
                try:
                    _check_redirect(final, target)
                except ValueError:
                    continue
                if target not in visited and target not in queue and len(queue) < 100:
                    queue.append(target)
        except (ValueError, OSError, http.client.HTTPException) as exc:
            errors.append({"url": url, "error": str(exc), "retryable": is_retryable_error(exc)})
    return articles, errors
