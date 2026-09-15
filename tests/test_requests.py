import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class RequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        package = types.ModuleType("_request_test")
        package.__path__ = []
        util = types.SimpleNamespace(append_default_headers=lambda headers: headers, PROXIES={}, REQUEST_TIMEOUT=300,
                                     printD=lambda _: None, indented_msg=lambda text: text)
        cls.modules = patch.dict(sys.modules, {"_request_test":package,"_request_test.util":util,"_request_test.model":types.ModuleType("model")})
        cls.modules.start()
        spec = importlib.util.spec_from_file_location("_request_test.downloader", root / "ch_lib/downloader.py")
        cls.downloader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.downloader)

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def test_invalid_filters_are_not_retried_and_search_timeout_is_used(self):
        response = types.SimpleNamespace(ok=False,status_code=400,reason="Bad Request")
        with patch.object(self.downloader.requests,"get",return_value=response) as get:
            result = self.downloader.request_get("https://civitai.com/api/v1/models",max_retries=1,timeout=20)
        self.assertFalse(result[0])
        self.assertEqual(get.call_count,1)
        self.assertEqual(get.call_args.kwargs["timeout"],20)

    def test_transient_error_retry_is_bounded(self):
        response = types.SimpleNamespace(ok=False,status_code=503,reason="Unavailable")
        with patch.object(self.downloader.requests,"get",return_value=response) as get, patch.object(self.downloader.time,"sleep"):
            result = self.downloader.request_get("https://civitai.com/api/v1/models",max_retries=1,timeout=20)
        self.assertFalse(result[0])
        self.assertEqual(get.call_count,2)

    def test_timeout_returns_a_chinese_error(self):
        with patch.object(self.downloader.requests,"get",side_effect=self.downloader.requests.Timeout()):
            result = self.downloader.request_get("https://civitai.com/api/v1/models",max_retries=1,timeout=20)
        self.assertFalse(result[0])
        self.assertIn("超时",result[1])


if __name__ == "__main__":
    unittest.main()
