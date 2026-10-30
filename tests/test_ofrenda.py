#!/usr/bin/env python3
"""Automated tests for Ofrenda Keeper (standard-library unittest).

Run from the project folder:  python -m unittest discover -s tests -v
No Ollama or network needed — the model is stubbed wherever a test
needs it.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ofrenda", ROOT / "ofrenda.py")
of = importlib.util.module_from_spec(spec)
spec.loader.exec_module(of)

PERSON = {"name": "Dada Ji", "dates": "1940 - 2019", "place": "Bahawalpur",
          "memory": "He read the newspaper aloud every sunrise.", "source": "x.txt"}


class TestParsing(unittest.TestCase):
    def write(self, tmp, text):
        p = Path(tmp) / "m.txt"
        p.write_text(text, encoding="utf-8")
        return p

    def test_all_fields_parsed(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        p = of.parse_memory_file(self.write(tmp, "Name: A\nDates: 1900-2000\nPlace: X\nMemory: hello world\n"))
        self.assertEqual((p["name"], p["dates"], p["place"], p["memory"]),
                         ("A", "1900-2000", "X", "hello world"))

    def test_multiline_memory_joined(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        p = of.parse_memory_file(self.write(tmp, "Name: A\nMemory: line one\nline two\n"))
        self.assertEqual(p["memory"], "line one line two")

    def test_missing_name_falls_back_to_filename(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        d = Path(tmp)
        (d / "my_grandfather.txt").write_text("Memory: kind man.\n", encoding="utf-8")
        self.assertEqual(of.parse_memory_file(d / "my_grandfather.txt")["name"], "My Grandfather")

    def test_unknown_lines_ignored(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        p = of.parse_memory_file(self.write(tmp, "Name: A\nHobby: chess\nMemory: ok\n"))
        self.assertNotIn("chess", p["memory"])
        self.assertEqual(p["name"], "A")


class TestEchoGuard(unittest.TestCase):
    def test_placeholder_tribute_rejected(self):
        self.assertIsNone(of.clean_tribute("<the person's name: Dada Ji>", PERSON))
        self.assertIsNone(of.clean_tribute("job title", PERSON))

    def test_empty_and_tiny_rejected(self):
        self.assertIsNone(of.clean_tribute("", PERSON))
        self.assertIsNone(of.clean_tribute("He was nice.", PERSON))

    def test_real_tribute_accepted(self):
        t = ("Dada Ji rose before the sun and shared his newspaper with anyone "
             "who would listen, turning hard words into lessons.")
        self.assertEqual(of.clean_tribute(t, PERSON), t)

    def test_fallback_names_the_person(self):
        self.assertIn("Dada Ji", of.fallback_tribute(PERSON))


class TestHtmlSafety(unittest.TestCase):
    def test_memory_html_is_escaped(self):
        evil = dict(PERSON, memory='<script>alert("x")</script>', tribute="Lovely.", engine="gemma-local")
        html_out = of.build_html([evil])
        self.assertNotIn("<script>", html_out)
        self.assertIn("&lt;script&gt;", html_out)

    def test_name_html_is_escaped(self):
        evil = dict(PERSON, name="A <b>bold</b> name", tribute="Lovely.", engine="gemma-local", memory="")
        self.assertNotIn("<b>bold</b>", of.build_html([evil]))

    def test_page_is_self_contained(self):
        html_out = of.build_html([dict(PERSON, tribute="Lovely.", engine="gemma-local")])
        self.assertIn("<style>", html_out)
        self.assertNotIn("http://", html_out.replace("http://localhost", ""))
        self.assertNotIn("https://", html_out)


class TestEndToEnd(unittest.TestCase):
    def test_full_run_with_stubbed_model(self):
        import tempfile, csv
        tmp = Path(tempfile.mkdtemp())
        mem = tmp / "memories"
        mem.mkdir()
        (mem / "a.txt").write_text("Name: Dada Ji\nDates: 1940-2019\nMemory: sunrise reader.\n", encoding="utf-8")
        (mem / "b.txt").write_text("Name: Miss Amina\nMemory: <b>not really html</b>\n", encoding="utf-8")
        # stub the model: one real tribute, one echo (must fall back)
        calls = {"n": 0}
        def fake_ask(model, person):
            calls["n"] += 1
            if person["name"] == "Dada Ji":
                return ("Dada Ji greeted every sunrise with a newspaper, turning "
                        "headlines into lessons for whoever sat beside him.")
            return "<the person's name>"
        real_ask = of.ask_gemma_tribute
        of.ask_gemma_tribute = fake_ask
        try:
            self.assertEqual(of.main([str(mem), "--out", str(tmp / "out")]), 0)
        finally:
            of.ask_gemma_tribute = real_ask
        page = (tmp / "out" / "ofrenda.html").read_text(encoding="utf-8")
        self.assertIn("Dada Ji", page)
        self.assertIn("Miss Amina", page)
        self.assertIn("gemma-local", page)
        self.assertIn("fallback-rules", page)   # the echo was honestly labelled
        self.assertNotIn("<b>not really html</b>", page)
        self.assertEqual(calls["n"], 2)

    def test_empty_folder_exits_gracefully(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "empty").mkdir()
        self.assertEqual(of.main([str(tmp / "empty"), "--out", str(tmp / "o")]), 1)


if __name__ == "__main__":
    unittest.main()
