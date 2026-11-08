import json
import unittest

from helpers import APEX_PY  # noqa: F401  (sets sys.path)
from apex_core import searchlog


class Extract(unittest.TestCase):
    def assertFinds(self, payload, *urls):
        found = searchlog.extract(payload)
        for u in urls:
            self.assertIn(u, found)

    def test_any_payload_shape(self):
        shapes = [
            {"results": [{"tool_use_id": "t", "content": [{"title": "G2", "url": "https://www.g2.com/p/x/reviews"}]}]},
            [{"type": "text", "text": "Source: https://www.g2.com/p/x/reviews"}],
            "Plain text with https://www.g2.com/p/x/reviews inside.",
            {"deeply": {"nested": [[{"k": ["https://www.g2.com/p/x/reviews"]}]]}},
            {"https://www.g2.com/p/x/reviews": "url used as a key"},
            json.dumps({"stringified": {"url": "https://www.g2.com/p/x/reviews"}}),
            r'{"escaped":"https:\/\/www.g2.com\/p\/x\/reviews"}',
            {"result": "{\"url\": \"https://www.g2.com/p/x/reviews\"}"},
        ]
        for shape in shapes:
            with self.subTest(shape=shape):
                self.assertFinds(shape, "https://www.g2.com/p/x/reviews")

    def test_markdown_and_prose_delimiters(self):
        text = ("[HN](https://news.ycombinator.com/item?id=1). <https://reddit.com/r/saas/comments/a/> "
                "(https://github.com/o/r/issues/9), 'https://example.com/q?a=1&b=2'; "
                "https://en.wikipedia.org/wiki/Foo_(bar) end")
        self.assertEqual(searchlog.extract(text), [
            "https://news.ycombinator.com/item?id=1", "https://reddit.com/r/saas/comments/a/",
            "https://github.com/o/r/issues/9", "https://example.com/q?a=1&b=2",
            "https://en.wikipedia.org/wiki/Foo_(bar)"])

    def test_urls_nested_in_redirects(self):
        found = searchlog.extract({"u": "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fcapterra.com%2Fp%2F1&rut=x"})
        self.assertTrue(any(u.startswith("https://capterra.com/p/1") for u in found), found)

    def test_input_and_response_are_both_scanned(self):
        event = {"tool_input": {"url": "https://acme.example.com/pricing", "prompt": "extract prices"},
                 "tool_response": {"result": "See https://acme.example.com/changelog"}}
        self.assertFinds(event, "https://acme.example.com/pricing", "https://acme.example.com/changelog")

    def test_no_false_urls(self):
        self.assertEqual(searchlog.extract({"q": "http:// and https://x and ftp://a.b/c and no urls"}), [])

    def test_normalize(self):
        self.assertEqual(searchlog.normalize("http://www.Example.com/a/?utm_source=x&b=1#frag"),
                         "https://example.com/a?b=1")
        self.assertEqual(searchlog.normalize("https://example.com/a)."), "https://example.com/a")


if __name__ == "__main__":
    unittest.main()
