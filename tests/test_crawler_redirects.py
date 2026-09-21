import http.client
import ssl
import unittest
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.crawler import MAX_REDIRECTS, crawl, fetch, is_retryable_error


@contextmanager
def network(routes, addresses=None):
    """Exercise real fetch/robots logic with only the network boundary mocked."""
    requests = []
    addresses = addresses or {}

    def resolve(host, port, **kwargs):
        return [(2, 1, 6, "", (addresses.get(host, "93.184.216.34"), port))]

    def connection(host, port, timeout):
        client = Mock()

        def request(method, path, headers):
            scheme = "https" if port == 443 else "http"
            client.requested_url = f"{scheme}://{host}{path}"
            requests.append(client.requested_url)

        def respond():
            result = routes[client.requested_url]
            if isinstance(result, Exception):
                raise result
            status, headers, body = result
            response = Mock(status=status)
            response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
            response.read.return_value = body.encode("utf-8")
            return response

        client.request.side_effect = request
        client.getresponse.side_effect = respond
        return client

    tls = Mock()
    tls.wrap_socket.side_effect = lambda sock, server_hostname: sock
    with ExitStack() as stack:
        dns = stack.enter_context(patch("app.crawler.socket.getaddrinfo", side_effect=resolve))
        connect = stack.enter_context(patch("app.crawler.socket.create_connection", side_effect=lambda *a, **k: Mock()))
        stack.enter_context(patch("app.crawler.http.client.HTTPConnection", side_effect=connection))
        context = stack.enter_context(patch("app.crawler.ssl.create_default_context", return_value=tls))
        sleep = stack.enter_context(patch("app.crawler.time.sleep"))
        yield SimpleNamespace(requests=requests, connect=connect, dns=dns, tls=tls, context=context, sleep=sleep)


def redirect(target):
    return 301, {"Location": target}, ""


def html(body="<title>Artikel</title><p>Isi artikel</p>"):
    return 200, {"Content-Type": "text/html; charset=utf-8"}, body


def robots(body="", status=200):
    return status, {"Content-Type": "text/plain"}, body


class CrawlerRedirectTests(unittest.TestCase):
    def test_upgrade_and_www_redirect_pin_dns_and_verify_tls(self):
        for source, target in [
            ("http://example.org/article", "https://www.example.org/article"),
            ("https://www.example.org/article", "https://example.org/article"),
        ]:
            with self.subTest(source=source), network({source: redirect(target), target: html()}) as net:
                final, status, body = fetch(source)
                self.assertEqual((final, status), (target, 200))
                self.assertIn("Isi artikel", body)
                self.assertEqual(net.requests, [source, target])
                self.assertEqual(net.dns.call_count, 2)
                self.assertEqual(net.connect.call_args.args[0], ("93.184.216.34", 443))
                self.assertEqual(net.tls.wrap_socket.call_args.kwargs["server_hostname"], target.split("/")[2])
                net.context.assert_called()

    def test_denies_unsafe_redirects_before_contacting_target(self):
        source = "https://example.org/article"
        for target in [
            "https://other.org/article",
            "https://news.example.org/article",
            "https://example.org.evil.org/article",
            "http://example.org/article",
            "file:///etc/passwd",
            "https://user:pass@example.org/article",
            "https://@example.org/article",
            "https://example.org:8000/article",
        ]:
            with self.subTest(target=target), network({source: redirect(target)}) as net:
                with self.assertRaises(ValueError):
                    fetch(source)
                self.assertEqual(net.requests, [source])
                self.assertEqual(net.connect.call_count, 1)

    def test_redirect_target_dns_is_validated_before_connection(self):
        source, target = "https://example.org/article", "https://www.example.org/article"
        for address in ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"]:
            with self.subTest(address=address), network({source: redirect(target)}, {"www.example.org": address}) as net:
                with self.assertRaisesRegex(ValueError, "privat"):
                    fetch(source)
                self.assertEqual(net.requests, [source])
                self.assertEqual(net.connect.call_count, 1)

    def test_same_hostname_dns_is_rechecked_on_every_hop(self):
        source, target = "https://example.org/article", "https://example.org/new"
        with network({source: redirect(target)}) as net:
            net.dns.side_effect = [
                [(2, 1, 6, "", ("93.184.216.34", 443))],
                [(2, 1, 6, "", ("127.0.0.1", 443))],
            ]
            with self.assertRaisesRegex(ValueError, "privat"):
                fetch(source)
            self.assertEqual(net.requests, [source])

    def test_redirect_loops_and_long_chains_are_bounded(self):
        source, target = "https://example.org/article", "https://example.org/new"
        with network({source: redirect(target), target: redirect(source)}) as net:
            with self.assertRaisesRegex(ValueError, "berulang"):
                fetch(source)
            self.assertEqual(net.requests, [source, target])
        routes = {f"https://example.org/{i}": redirect(f"/{i + 1}") for i in range(MAX_REDIRECTS + 1)}
        with network(routes) as net:
            with self.assertRaisesRegex(ValueError, "Terlalu banyak redirect"):
                fetch("https://example.org/0")
            self.assertEqual(len(net.requests), MAX_REDIRECTS + 1)

    def test_new_origin_robots_checked_before_redirected_article(self):
        source, target = "http://example.org/article", "https://www.example.org/article"
        source_robots, target_robots = "http://example.org/robots.txt", "https://www.example.org/robots.txt"
        routes = {source_robots: robots(status=404), source: redirect(target), target_robots: robots(), target: html()}
        with network(routes) as net, patch("app.crawler.trafilatura.extract", return_value="Isi bukti lengkap. " * 20):
            articles, errors = crawl(source)
        self.assertFalse(errors)
        self.assertEqual(articles[0]["url"], target)
        self.assertEqual(net.requests, [source_robots, source, target_robots, target])
        self.assertEqual(net.sleep.call_count, 2)

    def test_scheme_upgrade_checks_new_origin_robots_even_with_same_host(self):
        source, target = "http://example.org/article", "https://example.org/article"
        routes = {
            "http://example.org/robots.txt": robots(),
            source: redirect(target),
            "https://example.org/robots.txt": robots("User-agent: *\nDisallow: /article"),
        }
        with network(routes) as net:
            articles, errors = crawl(source)
        self.assertFalse(articles)
        self.assertIn("robots.txt", errors[0]["error"])
        self.assertFalse(errors[0]["retryable"])
        self.assertNotIn(target, net.requests)

    def test_target_robots_denial_or_403_never_fetches_article(self):
        source, target = "https://example.org/article", "https://www.example.org/article"
        for target_policy in [robots("User-agent: *\nDisallow: /article"), robots(status=403)]:
            routes = {
                "https://example.org/robots.txt": robots(),
                source: redirect(target),
                "https://www.example.org/robots.txt": target_policy,
            }
            with self.subTest(status=target_policy[0]), network(routes) as net:
                articles, errors = crawl(source)
                self.assertFalse(articles)
                self.assertIn("robots.txt", errors[0]["error"])
                if target_policy[0] == 403:
                    self.assertIn("HTTP 403", errors[0]["error"])
                self.assertFalse(errors[0]["retryable"])
                self.assertNotIn(target, net.requests)

    def test_seed_robots_http_failure_has_clear_status_and_retry_hint(self):
        for status in [403, 429, 503]:
            with self.subTest(status=status), network({"https://example.org/robots.txt": robots(status=status)}) as net:
                with self.assertRaisesRegex(ValueError, f"robots.txt.*HTTP {status}") as raised:
                    crawl("https://example.org/article")
                self.assertEqual(is_retryable_error(raised.exception), status != 403)
                self.assertEqual(net.requests, ["https://example.org/robots.txt"])

    def test_article_status_marks_only_transient_http_failures_retryable(self):
        source = "https://example.org/article"
        for status in [403, 404, 408, 429, 500, 502, 503, 504]:
            routes = {"https://example.org/robots.txt": robots(), source: robots(status=status)}
            with self.subTest(status=status), network(routes):
                articles, errors = crawl(source)
                self.assertFalse(articles)
                self.assertIn(f"HTTP {status}", errors[0]["error"])
                self.assertEqual(errors[0]["retryable"], status not in {403, 404})

    def test_retry_hint_distinguishes_transport_failure_from_tls_failure(self):
        source = "https://example.org/article"
        for failure in [TimeoutError("timeout"), ConnectionResetError("reset"), http.client.RemoteDisconnected(), ssl.SSLCertVerificationError("certificate")]:
            routes = {"https://example.org/robots.txt": robots(), source: failure}
            with self.subTest(failure=type(failure).__name__), network(routes):
                articles, errors = crawl(source)
                self.assertFalse(articles)
                self.assertEqual(errors[0]["retryable"], not isinstance(failure, ssl.SSLError))


if __name__ == "__main__":
    unittest.main()
