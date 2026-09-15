import copy
import importlib
import os
from pathlib import Path
import sys
import types
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from browser.catalog import CATALOG, MODEL_TYPE_CHOICES, base_choices, expand_base_models
from browser.search import make_params, search_page, trusted_next_page

ENDPOINT = "https://civitai.com/api/v1/models?"


class FilterTests(unittest.TestCase):
    def test_modern_models_and_types_are_available(self):
        names = dict((value, label) for label, value in base_choices())
        for name in ["Anima", "NoobAI", "Qwen", "Flux.2 Klein 9B", "ZImageBase", "Wan Video 2.2 I2V-A14B"]:
            self.assertIn(name, names)
        self.assertTrue({"TextEncoder", "UNet", "Detection", "VisionLanguage", "ComfyWorkflows", "LLM"}.issubset({value for _, value in MODEL_TYPE_CHOICES}))

    def test_family_expansion_and_explicit_variant(self):
        family = expand_base_models(families=["Stability AI"])
        self.assertIn("SD 1.5", family)
        self.assertIn("SDXL 1.0", family)
        self.assertNotIn("Qwen", family)
        self.assertEqual(expand_base_models(["SDXL 1.0"], ["Stability AI"]), ["SDXL 1.0"])
        self.assertEqual(expand_base_models(), [])

    def test_historical_models_and_custom_names(self):
        active = {value for _, value in base_choices()}
        historical = {value for _, value in base_choices(include_legacy=True)}
        self.assertIn("SDXL 0.9", historical - active)
        self.assertEqual(expand_base_models(["Flux .1 D", "Flux.1 D", "New Model"]), ["Flux.1 D", "New Model"])

    def test_url_encoding_keeps_filters_and_chinese_query_intact(self):
        query = make_params({"query":"花 & sky=blue", "baseModels":["SD 1.5", "Flux.1 D"], "types":["LORA", "TextEncoder"], "nsfw":False})
        parsed = parse_qs(query)
        self.assertEqual(parsed["query"], ["花 & sky=blue"])
        self.assertEqual(parsed["baseModels"], ["SD 1.5", "Flux.1 D"])
        self.assertEqual(parsed["types"], ["LORA", "TextEncoder"])
        self.assertEqual(parsed["nsfw"], ["false"])


class PaginationTests(unittest.TestCase):
    def test_forward_backward_and_new_search_reset(self):
        def fetch(url):
            cursor = parse_qs(urlsplit(url).query).get("cursor", ["0"])[0]
            return {"items": [], "metadata": {"nextPage": ENDPOINT + "cursor=" + str(int(cursor) + 1)}}
        params = {"query":"flowers"}
        first, _, prev, next_ = search_page({}, params, "search", fetch, ENDPOINT)
        self.assertFalse(prev)
        self.assertTrue(next_)
        second, _, prev, _ = search_page(first, params, "next", fetch, ENDPOINT)
        self.assertEqual(second["current_page"], 1)
        self.assertTrue(prev)
        back, *_ = search_page(second, params, "previous", fetch, ENDPOINT)
        self.assertEqual(back["current_page"], 0)
        reset, *_ = search_page(second, {"query":"trees"}, "search", fetch, ENDPOINT)
        self.assertEqual(reset["current_page"], 0)
        self.assertIn("trees", reset["pages"][0])
        self.assertNotIn(first["pages"][0], reset["pages"])

    def test_failed_fetch_does_not_mutate_history(self):
        state = {"current_page":0, "pages":[ENDPOINT+"query=x", ENDPOINT+"cursor=2"], "query":ENDPOINT+"query=x"}
        original = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            search_page(state, {"query":"x"}, "next", lambda _:None, ENDPOINT)
        self.assertEqual(state, original)

    def test_invalid_or_repeating_next_cursor_disables_next(self):
        for url in [None, "https://example.com/api/v1/models?cursor=1", "https://civitai.com:bad/api/v1/models", "https://user:secret@civitai.com/api/v1/models"]:
            self.assertIsNone(trusted_next_page(url, ENDPOINT))
        state, _, _, next_ = search_page({}, {}, "search", lambda _:{"items":[], "metadata":{"nextPage":ENDPOINT}}, ENDPOINT)
        self.assertFalse(next_)
        self.assertEqual(len(state["pages"]), 1)


class BrowserUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gradio
        cls.gr = gradio
        cls.civitai = types.ModuleType("ch_lib.civitai")
        cls.civitai.URLS = {"query":ENDPOINT,"modelPage":"https://civitai.com/models/"}
        cls.civitai.NSFW_LEVELS = {"PG":1,"PG13":2}
        cls.civitai.civitai_get = lambda *args, **kwargs: None
        cls.util = types.ModuleType("ch_lib.util")
        cls.util.script_dir = str(ROOT)
        cls.util.get_opts = lambda _: "PG13"
        cls.modules = patch.dict(sys.modules, {"ch_lib.util":cls.util,"ch_lib.civitai":cls.civitai})
        cls.modules.start()
        cls.browser = importlib.import_module("browser.browser")

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def test_real_gradio_build_and_error_output_arity(self):
        ui = self.browser.civitai_search()
        controls = {c.get("props", {}).get("elem_id"):c for c in ui.config["components"]}
        self.assertEqual(controls["ch_browser_types"]["props"]["label"], "模型类型")
        self.assertEqual(len(controls["ch_browser_types"]["props"]["choices"]), len(CATALOG["model_types"]))
        function = next(fn.fn for fn in ui.fns.values() if fn.fn and fn.fn.__name__ == "perform_search")
        button = ui.blocks[controls["ch_browser_search"]["id"]]
        output = function({}, "x", "", "", "AllTime", "Newest", [], [], [], False, "", 20, False, self.gr.EventData(button, {}))
        self.assertEqual(len(output), 5)
        self.assertIn("搜索失败", output[-1])
        clear = next(fn.fn for fn in ui.fns.values() if fn.fn and fn.fn.__name__ == "clear_filters")
        self.assertEqual(len(clear()), 17)

    def test_preview_threshold_null_description_and_escaping(self):
        model = {"id":123, "name":'<img src=x onerror="alert(1)">', "type":"TextEncoder", "description":None,
                 "modelVersions":[{"id":1,"baseModel":"Qwen","images":[
                     {"url":"https://image.civitai.com/adult.jpg","type":"image","nsfwLevel":8},
                     {"url":"https://image.civitai.com/allowed.jpg","type":"image","nsfwLevel":2}]}]}
        parsed = self.browser.parse_model(model)
        self.assertTrue(parsed["preview"]["url"].endswith("allowed.jpg"))
        card = self.browser.make_cards([parsed])[0]
        self.assertIn("&lt;img", card)
        self.assertNotIn('<img src=x', card)
        self.assertIn("文本编码器", card)
        self.assertIn("暂无说明", card)
        model["description"] = '<script>alert(1)</script><p>Safe &amp; sound</p>'
        card = self.browser.make_cards([self.browser.parse_model(model)])[0]
        self.assertNotIn('<script>', card)
        self.assertIn('Safe &amp; sound', card)


if __name__ == "__main__":
    unittest.main()
