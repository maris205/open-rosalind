import http.cookiejar
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from web_app import server


class DesktopAccessTests(unittest.TestCase):
    token = "a" * 64

    def setUp(self) -> None:
        self.desktop_mode = patch.object(server, "DESKTOP_MODE", True)
        self.desktop_token = patch.object(server, "DESKTOP_TOKEN", self.token)
        self.desktop_mode.start()
        self.desktop_token.start()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.desktop_token.stop()
        self.desktop_mode.stop()

    def test_desktop_api_rejects_requests_without_transport_cookie(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(f"{self.base_url}/api/config", timeout=2)

        self.assertEqual(context.exception.code, 403)

    def test_bootstrap_sets_http_only_cookie_and_unlocks_local_api(self) -> None:
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )

        response = opener.open(
            f"{self.base_url}/desktop/bootstrap?token={self.token}", timeout=2
        )
        self.assertTrue(response.geturl().endswith("/app"))
        self.assertEqual(response.status, 200)
        desktop_cookies = [
            cookie for cookie in cookie_jar if cookie.name == server.DESKTOP_COOKIE_NAME
        ]
        self.assertEqual(len(desktop_cookies), 1)
        self.assertTrue(desktop_cookies[0].has_nonstandard_attr("HttpOnly"))

        config = opener.open(f"{self.base_url}/api/config", timeout=2)
        self.assertEqual(config.status, 200)

    def test_bootstrap_rejects_an_invalid_token(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(
                f"{self.base_url}/desktop/bootstrap?token={'b' * 64}", timeout=2
            )

        self.assertEqual(context.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
