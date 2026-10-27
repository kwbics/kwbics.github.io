"""Isolated CV mapping tests and content-independent PDF acceptance checks.

python -m unittest discover -s test -p test_export_cv.py -v
CV_RENDER_TESTS=1 enables real synthetic mutation renders.
RENDERCV_PDF and RENDERCV_YAML bind the live PDF check to its exported input.
"""

import base64
import copy
from html.parser import HTMLParser
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_data/cv.yml"
EXPORTER = ROOT / "bin/export_cv.py"
# Frozen synthetic input: no unit assertion depends on today's public biography.
SAMPLE = """
cv:
  name: Alex Example
  label: Professor; Co-founder and CIO at Example Semiconductor
  email: alex@example.org
  location: Sample City, Republic of Korea
  image: ""
  summary: Professor of Electrical Engineering, directing Example's Circuit Lab since 2018.
  social_networks:
    - network: Google Scholar
      username: ExampleScholarID
    - network: GitHub
      username: example
  address:
    city: Sample City
    region: Sample Region
    countryCode: KR
  sections:
    Industry Role:
      - label: Co-founder and CIO, Example Semiconductor
        details: Interface design and FPGA data capture.
    Education:
      - institution: Example University
        location: Example Campus
        area: Electrical Engineering
        studyType: Ph.D.
        start_date: 2009
        end_date: 2013
    Experience:
      - company: Example Institute
        position: Research Professor
        start_date: 2017-03-01
        end_date: Present
    Awards:
      - title: Example Design Award
        date: 2014
"""
# A real, portable 1x1 PNG for repository-root asset resolution tests.
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYPgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
)

# Frozen JPEG exercises the exact website assets/img/prof_pic.jpg path.
JPEG = base64.b64decode(
    '/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQA'
    'AAABAAAAAaADAAQAAAABAAAAAQAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmA'
    'CZjs+EJ+/8AAEQgAAQABAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQE'
    'AAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldY'
    'WVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk'
    '5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMR'
    'BAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdo'
    'aWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz'
    '9PX29/j5+v/bAEMAAgICAgICAwICAwUDAwMFBgUFBQUGCAYGBgYGCAoICAgICAgKCgoKCgoKCgwMDAwMDA4ODg4ODw8PDw8PDw8P'
    'D//bAEMBAgICBAQEBwQEBxALCQsQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEP/dAAQA'
    'Af/aAAwDAQACEQMRAD8A/HOiiiv9/D8rP//Z'
)


def canonical(value):
    """Normalize typography only; retain every digit, date separator and word."""
    value = value.translate(str.maketrans({"’": "'", "‘": "'", "\u00ad": ""}))
    return re.sub(r"\s+", "", value)


class MarkdownText(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts, self.links = [], []
        import markdown
        self.feed(markdown.markdown(value))

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href")


def assert_pdf_fidelity(case, exported, pdf, document=None):
    """Walk every exported section leaf, including nested highlights and dates.

    Header display and date formatting use the installed RenderCV 2.8 functions
    and the same design/settings/locale as the rendering command. URLs are
    verified as PDF annotations; photos are verified as embedded PDF images.
    """
    from rendercv.renderer.templater.connections import parse_connections
    from rendercv.renderer.templater.date import format_date_range, format_single_date
    from rendercv.schema.rendercv_model_builder import build_rendercv_dictionary_and_model

    case.assertEqual(importlib.metadata.version("rendercv"), "2.8")
    case.assertGreater(pdf.stat().st_size, 1000)
    case.assertEqual(pdf.read_bytes()[:5], b"%PDF-")
    raw = document or yaml.safe_load(exported.read_text(encoding="utf-8"))
    _, model = build_rendercv_dictionary_and_model(
        yaml.safe_dump(raw), input_file_path=exported,
        design_yaml_file=(ROOT / "assets/rendercv/design.yaml").read_text(),
        locale_yaml_file=(ROOT / "assets/rendercv/locale.yaml").read_text(),
        settings_yaml_file=(ROOT / "assets/rendercv/settings.yaml").read_text(),
    )
    extracted = subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"], check=True, text=True, capture_output=True
    ).stdout
    actual = canonical(extracted)
    annotations = subprocess.run(
        ["pdfinfo", "-url", str(pdf)], check=True, text=True, capture_output=True
    ).stdout

    def expect_text(value, path):
        parsed = MarkdownText(str(value))
        visible = canonical("".join(parsed.parts))
        case.assertIn(visible, actual, f"Missing PDF content at {path}: {value!r}")
        for link in parsed.links:
            case.assertIn(link, annotations, f"Missing PDF link at {path}")

    templates = model.design.templates

    def walk(value, path):
        if isinstance(value, dict):
            if value.get("start_date") is not None and value.get("end_date") is not None:
                expected = format_date_range(
                    value["start_date"], value["end_date"], locale=model.locale,
                    single_date_template=templates.single_date, date_range_template=templates.date_range,
                )
                expect_text(expected, path + ".date_range")
            for key, child in value.items():
                if key in ("start_date", "end_date"):
                    continue
                if key == "date" and child is not None:
                    child = format_single_date(child, locale=model.locale, single_date_template=templates.single_date)
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{path}[{i}]")
        elif value is not None:
            expect_text(value, path)

    cv = raw["cv"]
    for key in ("name", "headline"):
        if cv.get(key):
            expect_text(cv[key], f"cv.{key}")
    for connection in parse_connections(model):
        expect_text(connection.body, "cv.connections")
        if connection.url and model.design.header.connections.hyperlink:
            case.assertIn(connection.url, annotations)
    for title, entries in cv["sections"].items():
        expect_text(title, "cv.sections title")
        walk(entries, f"cv.sections.{title}")
    if cv.get("photo"):
        images = subprocess.run(
            ["pdfimages", "-list", str(pdf)], check=True, text=True, capture_output=True
        ).stdout
        case.assertRegex(images, r"(?m)^\s*\d+\s+\d+\s+image\s", "Photo missing from PDF")


def assert_live_export_and_pdf(case, source_path, exported, pdf):
    """Bind an exported PDF to any source, independent of its content."""
    spec = importlib.util.spec_from_file_location("export_cv", EXPORTER)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    before = source_path.read_bytes()
    source = yaml.load(before.decode(), Loader=adapter.UniqueKeyLoader)
    expected = adapter.export_document(source, source_path.resolve(), exported)
    case.assertEqual(expected, yaml.safe_load(exported.read_text()))
    assert_pdf_fidelity(case, exported, pdf)
    case.assertEqual(before, source_path.read_bytes())


class ExportCVTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.directory = Path(self.workspace.name).resolve()
        self.source = self.directory / "_data/cv.yml"
        self.source.parent.mkdir()
        self.output = self.directory / "output/cv/rendercv.yaml"
        self.document = yaml.safe_load(SAMPLE)
        photo = self.directory / "assets/img/portrait.png"
        photo.parent.mkdir(parents=True)
        photo.write_bytes(PIXEL)
        (photo.parent / "prof_pic.jpg").write_bytes(JPEG)

    def run_export(self, source=None, output=None, seed=None):
        return subprocess.run(
            [sys.executable, str(EXPORTER), "--input", str(source or self.source),
             "--output", str(output or self.output)], text=True, capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed or 1)}, check=False,
        )

    def export(self, document=None, raw=None):
        self.source.write_text(
            raw if raw is not None else yaml.safe_dump(
                self.document if document is None else document, allow_unicode=True
            ), encoding="utf-8"
        )
        return self.run_export()

    def result(self):
        result = self.export()
        self.assertEqual(result.returncode, 0, result.stderr)
        return yaml.safe_load(self.output.read_text(encoding="utf-8"))["cv"]

    def test_frozen_sample_mapping(self):
        cv = self.result()
        original = self.document["cv"]
        self.assertEqual(cv["name"], original["name"])
        self.assertEqual(cv["headline"], original["label"])
        self.assertEqual(cv["sections"]["Summary"], [original["summary"]])
        self.assertEqual(cv["sections"]["Industry Role"], original["sections"]["Industry Role"])
        self.assertEqual(cv["sections"]["Education"][0]["degree"], "Ph.D.")
        self.assertEqual(cv["sections"]["Education"][0]["start_date"], 2009)
        self.assertEqual(cv["sections"]["Education"][0]["end_date"], 2013)
        self.assertEqual(cv["sections"]["Experience"][0]["start_date"], "2017-03-01")
        self.assertEqual(cv["sections"]["Experience"][0]["end_date"], "present")
        self.assertEqual(cv["sections"]["Awards"], [{"name": "Example Design Award", "date": 2014}])
        self.assertEqual(cv["social_networks"], original["social_networks"])
        self.assertEqual(cv["location"], "Sample City, Sample Region, Republic of Korea")
        for field in ("label", "summary", "address", "image", "photo"):
            self.assertNotIn(field, cv)

    def test_live_source_is_unchanged_and_export_deterministic(self):
        before = SOURCE.read_bytes()
        first = self.run_export(source=SOURCE, seed=1)
        self.assertEqual(first.returncode, 0, first.stderr)
        expected = self.output.read_bytes()
        second = self.run_export(source=SOURCE, seed=42)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(expected, self.output.read_bytes())
        self.assertEqual(before, SOURCE.read_bytes())

    def test_output_cannot_overwrite_input_or_link(self):
        self.source.write_text(SAMPLE)
        before = self.source.read_bytes()
        for target in (self.source, self.directory / "symlink.yml", self.directory / "hardlink.yml"):
            if target.name == "symlink.yml":
                target.symlink_to(self.source)
            elif target.name == "hardlink.yml":
                os.link(self.source, target)
            result = self.run_export(output=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("same file", result.stderr)
            self.assertEqual(self.source.read_bytes(), before)

    def test_photo_resolves_from_repository_root(self):
        for image in ("assets/img/prof_pic.jpg", "/assets/img/prof_pic.jpg", "assets/img/portrait.png"):
            self.document["cv"]["image"] = image
            self.assertEqual(self.result()["photo"], "../../" + image.lstrip("/"))
        self.document["cv"]["image"] = "https://example.org/portrait.png"
        self.assertEqual(self.result()["photo"], "https://example.org/portrait.png")

    def test_missing_photo_rejected(self):
        self.document["cv"]["image"] = "assets/img/missing.png"
        result = self.export()
        self.assertEqual(result.returncode, 1)
        self.assertIn("cv.image", result.stderr)
        self.assertFalse(self.output.exists())

    def test_address_street_and_other_meaningful_fields(self):
        self.document["cv"]["location"] = "Campus, Other City, Other Country"
        self.document["cv"]["address"] = {
            "street": "123 Main St", "city": "Other City", "region": "Other Region",
            "postalCode": "01234", "country": "Other Country", "countryCode": "XX",
        }
        location = self.result()["location"]
        for value in self.document["cv"]["address"].values():
            self.assertIn(value, location)
        self.assertIn("Campus", location)
        self.assertEqual(location.count("Other City"), 1)
        self.assertEqual(location.count("Other Country"), 1)

    def test_common_employer_aliases_and_entry_urls(self):
        for alias in ("organization", "name"):
            doc = copy.deepcopy(self.document)
            entry = doc["cv"]["sections"]["Experience"][0]
            entry[alias] = entry.pop("company")
            for section in ("Education", "Experience", "Awards"):
                doc["cv"]["sections"][section][0]["url"] = "https://example.org/details"
            result = self.export(doc)
            self.assertEqual(result.returncode, 0, result.stderr)
            cv = yaml.safe_load(self.output.read_text())["cv"]
            self.assertEqual(cv["sections"]["Experience"][0]["company"],
                             "[Example Institute](https://example.org/details)")
            self.assertEqual(cv["sections"]["Education"][0]["institution"],
                             "[Example University](https://example.org/details)")
            self.assertEqual(cv["sections"]["Awards"][0]["name"],
                             "[Example Design Award](https://example.org/details)")

    def test_unknown_nonempty_fields_fail_with_source_path(self):
        mutations = [
            (lambda d: d.update({"unknown": "content"}), "source.unknown"),
            (lambda d: d["cv"].update({"unknown": "content"}), "cv.unknown"),
            (lambda d: d["cv"]["address"].update({"unknown": "content"}), "cv.address.unknown"),
            (lambda d: d["cv"]["social_networks"][0].update({"unknown": "content"}), "social_networks[0].unknown"),
            (lambda d: d["cv"]["sections"]["Education"][0].update({"thesis": "content"}), "Education[0].thesis"),
            (lambda d: d["cv"]["sections"]["Industry Role"][0].update({"start_date": 2020}), "Industry Role[0].start_date"),
        ]
        for mutate, path in mutations:
            with self.subTest(path=path):
                document = copy.deepcopy(self.document)
                mutate(document)
                result = self.export(document)
                self.assertEqual(result.returncode, 1)
                self.assertIn(path, result.stderr)
                self.assertFalse(self.output.exists())

    def test_malformed_source_is_rejected(self):
        invalid = [
            "", "[]", "cv: []", "cv: {name: A}",
            "cv: {name: A, sections: []}", "cv: {name: 17, sections: {}}",
            "cv: {name: A, sections: {Example: {label: X, details: Y}}}",
            "cv: {name: A, sections: {Example: [text, {name: X}]}}",
            "cv: {name: A, sections: {Example: [{label: X}]}}",
            "cv: {name: A, sections: {Example: [false]}}",
            "cv: {name: A, name: B, sections: {}}",
            "cv: {name: A, sections: {Example: [{name: X, date: 2026-02-30}]}}",
            "cv: {name: A, sections: {Example: [{name: X, date: true}]}}",
            "cv: {name: A, sections: {Example: [{company: X, position: Y, start_date: present}]}}",
            "cv: {name: A, sections: {Example: [{name: X, date: 2020, start_date: 2019}]}}",
            "cv: {name: A, summary: Biography, sections: {Summary: [Existing]}}",
            "cv: {name: A, sections: {Example: [{company: X, position: Y, start_date: 2017}]}}",
            "cv: {name: A, sections: {Example: [{company: X, position: Y, end_date: 2017}]}}",
            "cv: {name: A, sections: {Example: [{name: X, start_date: 2020, end_date: 2019}]}}",
            "cv: {name: A, sections: {Example: [{name: X, date: 2014, date: 2015}]}}",
            "cv: {name: A, sections: {}, unknown: false}",
            "cv: {name: A, sections: {}, unknown: 0}",
            "cv: {name: A, sections: {}, label: []}",
            "cv: {name: A, sections: {}, image: {}}",
            "cv: {name: A, sections: {}, address: []}",
            "cv: {name: A, sections: {}, address: {city: []}}",
            "cv: {name: A, sections: {}, social_networks: {}}",
            "cv: {name: A, sections: {Example: [{name: X, highlights: {}}]}}",
            "cv: {name: A, sections: {Example: [{institution: X, area: Y, studyType: []}]}}",
        ]
        for raw in invalid:
            with self.subTest(raw=raw):
                result = self.export(raw=raw)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("CV export error:", result.stderr)
                self.assertFalse(self.output.exists())

    @unittest.skipUnless(os.environ.get("CV_RENDER_TESTS"), "Set CV_RENDER_TESTS=1 for actual mutation renders")
    def test_valid_future_mutations_render(self):
        cases = {}
        for name in ("highlights", "award_month", "education_months", "rename_section", "change_location", "aliases_urls_photo", "employer_name", "minimal"):
            doc = copy.deepcopy(self.document)
            if name == "highlights":
                doc["cv"]["sections"]["Experience"][0]["highlights"] = ["Added mixed-signal design", "Added FPGA verification"]
                doc["cv"]["sections"]["Awards"][0]["summary"] = "Award context"
            elif name == "award_month":
                doc["cv"]["sections"]["Awards"][0]["date"] = "2014-11"
            elif name == "education_months":
                doc["cv"]["sections"]["Education"][0].update(start_date="2009-03", end_date="2013-02")
            elif name == "rename_section":
                doc["cv"]["sections"]["Entrepreneurship"] = doc["cv"]["sections"].pop("Industry Role")
            elif name == "change_location":
                doc["cv"]["location"] = "Leuven, Belgium"
                doc["cv"].pop("address")
            elif name == "aliases_urls_photo":
                experience = doc["cv"]["sections"]["Experience"][0]
                experience["organization"] = experience.pop("company")
                for section in ("Education", "Experience", "Awards"):
                    doc["cv"]["sections"][section][0]["url"] = f"https://example.org/{section.lower()}"
                doc["cv"]["address"]["street"] = "7 Campus Road"
                doc["cv"]["image"] = "/assets/img/prof_pic.jpg"
            elif name == "employer_name":
                experience = doc["cv"]["sections"]["Experience"][0]
                experience["name"] = experience.pop("company")
            else:
                doc = {"cv": {"name": "Another Example", "sections": {"Interests": ["Mixed-signal circuits"]}}}
            cases[name] = doc
        for name, document in cases.items():
            with self.subTest(mutation=name):
                result = self.export(document)
                self.assertEqual(result.returncode, 0, result.stderr)
                pdf = self.output.parent / f"{name}.pdf"
                process = subprocess.run(
                    [str(Path(sys.executable).parent / "rendercv"), "render", str(self.output),
                     "--settings", str(ROOT / "assets/rendercv/settings.yaml"),
                     "--design", str(ROOT / "assets/rendercv/design.yaml"),
                     "--locale-catalog", str(ROOT / "assets/rendercv/locale.yaml"),
                     "--pdf-path", str(pdf)], text=True, capture_output=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                assert_pdf_fidelity(self, self.output, pdf)
                assert_live_export_and_pdf(self, self.source, self.output, pdf)
                # Negative controls ensure the recursive check detects missing
                # list content and altered numeric/date content in a real PDF.
                wrong = yaml.safe_load(self.output.read_text())
                if name == "highlights":
                    wrong["cv"]["sections"]["Experience"][0]["highlights"].append("NOT IN THE PDF 987654321")
                    with self.assertRaises(AssertionError):
                        assert_pdf_fidelity(self, self.output, pdf, wrong)
                if name == "award_month":
                    wrong["cv"]["sections"]["Awards"][0]["date"] = "2014-12"
                    with self.assertRaises(AssertionError):
                        assert_pdf_fidelity(self, self.output, pdf, wrong)

    @unittest.skipUnless(os.environ.get("RENDERCV_PDF"), "Set RENDERCV_PDF after rendering the live CV")
    def test_rendered_pdf(self):
        pdf = Path(os.environ["RENDERCV_PDF"]).resolve()
        exported = Path(os.environ.get("RENDERCV_YAML", str(pdf.parent / "rendercv.yaml"))).resolve()
        assert_live_export_and_pdf(self, SOURCE, exported, pdf)


if __name__ == "__main__":
    unittest.main()
