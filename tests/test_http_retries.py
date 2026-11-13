import unittest
from unittest.mock import patch, Mock
import requests

from agrovision_http import get_with_retries


class RetryHttpTests(unittest.TestCase):
    @patch("agrovision_http.time.sleep")
    @patch("agrovision_http.requests.get")
    def test_retries_502_then_returns_success(self, mock_get, _sleep):
        bad = Mock(status_code=502, headers={})
        bad.raise_for_status.side_effect = requests.HTTPError("502 proxy error", response=bad)
        good = Mock(status_code=200)
        good.raise_for_status.return_value = None
        mock_get.side_effect = [bad, good]

        result = get_with_retries("https://example.test/data", attempts=3)

        self.assertIs(result, good)
        self.assertEqual(mock_get.call_count, 2)

    @patch("agrovision_http.time.sleep")
    @patch("agrovision_http.requests.get")
    def test_does_not_retry_non_transient_400(self, mock_get, _sleep):
        bad = Mock(status_code=400, headers={})
        bad.raise_for_status.side_effect = requests.HTTPError("400 bad request", response=bad)
        mock_get.return_value = bad

        with self.assertRaises(RuntimeError):
            get_with_retries("https://example.test/data", attempts=4)
        self.assertEqual(mock_get.call_count, 1)

    @patch("agrovision_http.time.sleep")
    @patch("agrovision_http.requests.get")
    def test_gives_clear_error_after_retry_limit(self, mock_get, _sleep):
        bad = Mock(status_code=502, headers={})
        bad.raise_for_status.side_effect = requests.HTTPError("502 proxy error", response=bad)
        mock_get.return_value = bad

        with self.assertRaisesRegex(RuntimeError, "after 2 attempt"):
            get_with_retries("https://example.test/data", attempts=2)
        self.assertEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
