#!/usr/bin/env python3
"""Export the website's CV to RenderCV 2.8 without changing the website schema.

Usage: python bin/export_cv.py --input _data/cv.yml --output output/cv/cv.yaml
Only explicitly supported fields are exported. Unsupported nonempty content,
ambiguous dates and malformed input fail before the output is written.
"""

import argparse
from datetime import date, datetime
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import yaml


class ExportError(ValueError):
    """A source value cannot be exported faithfully."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Prevent YAML duplicate keys from silently replacing biography facts."""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ExportError("YAML mapping keys must be strings")
            if key in result:
                raise ExportError(f"duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


# Keep dates as text until normalized_date can report their exact source path.
UniqueKeyLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in resolvers
          if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def empty(value):
    return value is None or (
        isinstance(value, (str, list, dict)) and not value
    ) or (isinstance(value, str) and not value.strip())


def mapping(value, path):
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ExportError(f"{path}: expected a mapping with string keys")
    return value


def known_fields(value, allowed, path):
    for key, content in value.items():
        if key not in allowed and not empty(content):
            raise ExportError(f"{path}.{key}: unsupported nonempty field")


def text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ExportError(f"{path}: expected nonempty text")
    return value


def normalized_date(value, path, *, arbitrary=False, allow_present=False):
    if isinstance(value, datetime) or isinstance(value, bool):
        raise ExportError(f"{path}: expected a year or date without a timestamp")
    if isinstance(value, date):
        value = value.isoformat()
    elif type(value) is int:
        value = str(value)
    value = text(value, path).strip()
    if value.lower() == "present":
        if allow_present:
            return "present"
        raise ExportError(f"{path}: present is only supported as end_date")
    if re.fullmatch(r"\d{4}(?:-\d{2})?(?:-\d{2})?", value):
        try:
            date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
        except ValueError as error:
            raise ExportError(f"{path}: invalid date {value}") from error
        return int(value) if len(value) == 4 else value
    if arbitrary:
        return value
    raise ExportError(f"{path}: expected YYYY, YYYY-MM, or YYYY-MM-DD")


COMMON = {"date", "start_date", "end_date", "location", "summary", "highlights", "url"}
ENTRY_FIELDS = {
    "education": ({"institution", "area", "studyType", "degree"} | COMMON, ("institution", "area")),
    "experience": ({"company", "organization", "name", "position"} | COMMON, ("position",)),
    "normal": ({"title", "name"} | COMMON, ()),
    "one_line": ({"label", "details"}, ("label", "details")),
}


def export_entry(value, path):
    if isinstance(value, str):
        return "text", text(value, path)
    entry = mapping(value, path)
    if "institution" in entry:
        kind = "education"
    elif "company" in entry or "organization" in entry or "position" in entry:
        kind = "experience"
    elif "name" in entry or "title" in entry:
        kind = "normal"
    elif "label" in entry or "details" in entry:
        kind = "one_line"
    else:
        raise ExportError(f"{path}: unsupported entry shape")
    allowed, required = ENTRY_FIELDS[kind]
    known_fields(entry, allowed, path)
    for field in required:
        text(entry.get(field), f"{path}.{field}")
    result = {}
    for field in allowed:
        if field in entry and entry[field] is not None:
            content = entry[field]
            if field == "highlights":
                if not isinstance(content, list):
                    raise ExportError(f"{path}.{field}: expected a list of text")
            elif field in ("date", "start_date", "end_date"):
                if isinstance(content, bool) or not isinstance(content, (str, int, date)):
                    raise ExportError(f"{path}.{field}: expected a year or date")
            elif not isinstance(content, str):
                raise ExportError(f"{path}.{field}: expected text")
        if field not in entry or empty(entry[field]):
            continue
        aliases = {"studyType": "degree", "title": "name"}
        if kind == "experience":
            aliases.update(organization="company", name="company")
        target = aliases.get(field, field)
        if target in result:
            raise ExportError(f"{path}: both {target} and its website alias were provided")
        content = entry[field]
        if field in ("date", "start_date", "end_date"):
            result[target] = normalized_date(
                content, f"{path}.{field}", arbitrary=field == "date", allow_present=field == "end_date"
            )
        elif field == "highlights":
            if not isinstance(content, list):
                raise ExportError(f"{path}.highlights: expected a list of text")
            result[target] = [text(item, f"{path}.highlights[{i}]") for i, item in enumerate(content)]
        else:
            result[target] = text(content, f"{path}.{field}")
    if kind == "experience" and "company" not in result:
        raise ExportError(f"{path}: company, organization or name is required with position")
    if kind == "normal" and "name" not in result:
        raise ExportError(f"{path}.name: a title or name is required")
    has_start, has_end = "start_date" in result, "end_date" in result
    if "date" in result and (has_start or has_end):
        raise ExportError(f"{path}: date cannot be combined with start_date/end_date")
    if has_start != has_end:
        raise ExportError(f"{path}: provide both start_date and end_date; dates are never inferred")
    if has_start and result["end_date"] != "present":
        # Compare without changing the precision retained in the exported YAML.
        start = (str(result["start_date"]) + "-01-01")[:10]
        end = (str(result["end_date"]) + "-01-01")[:10]
        if start > end:
            raise ExportError(f"{path}: start_date is after end_date")
    if "url" in result:
        url = result.pop("url")
        try:
            parsed = urlsplit(url)
        except ValueError as error:
            raise ExportError(f"{path}.url: invalid URL") from error
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ExportError(f"{path}.url: expected an absolute HTTP(S) URL")
        primary = {"education": "institution", "experience": "company", "normal": "name"}[kind]
        label = result[primary].replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
        # Parentheses delimit Markdown URLs; encoding preserves the link target.
        url = url.replace("(", "%28").replace(")", "%29")
        result[primary] = f"[{label}]({url})"
    # A fixed key order makes output independent of hash/set iteration order.
    order = ("institution", "area", "degree", "company", "position", "name", "label", "details",
             "location", "date", "start_date", "end_date", "summary", "highlights")
    return kind, {key: result[key] for key in order if key in result}



def normalized_location(cv):
    original = "" if empty(cv.get("location")) else text(cv["location"], "cv.location")
    if empty(cv.get("address")):
        return original
    address = mapping(cv["address"], "cv.address")
    fields = ("address", "street", "city", "region", "postalCode", "country", "countryCode")
    known_fields(address, set(fields), "cv.address")
    for field in fields:
        if field in address and address[field] is not None and not isinstance(address[field], str):
            raise ExportError(f"cv.address.{field}: expected text")
    values = {
        key: text(address[key], f"cv.address.{key}").strip()
        for key in fields if not empty(address.get(key))
    }
    if "street" in values:
        if "address" in values and values["address"] != values["street"]:
            raise ExportError("cv.address: address and street aliases conflict")
        values["address"] = values.pop("street")
    parts = [part.strip() for part in original.split(",") if part.strip()]
    countries = [values["country"]] if "country" in values else []
    code = values.get("countryCode", "")
    # This equivalence is explicit in the current source. Other codes are kept
    # verbatim rather than guessing a country name or discarding a field.
    country_alias = {"KR": "Republic of Korea"}.get(code.upper())
    if country_alias and any(part.casefold() == country_alias.casefold() for part in parts + countries):
        countries.append(country_alias)
        code = ""
    structured = [values[key] for key in ("address", "city", "region", "postalCode") if key in values]
    supplied = {part.casefold() for part in structured + countries + [values.get("countryCode", "")]}
    ordered = [part for part in parts if part.casefold() not in supplied] + structured + countries
    if code:
        ordered.append(code)
    result, seen = [], set()
    for part in ordered:
        if part.casefold() not in seen:
            result.append(part)
            seen.add(part.casefold())
    return ", ".join(result)


def export_document(document, source_path, output_path):
    source = mapping(document, "source")
    known_fields(source, {"cv"}, "source")
    cv = mapping(source.get("cv"), "cv")
    known_fields(cv, {"name", "label", "email", "phone", "website", "location", "image", "summary",
                      "social_networks", "address", "sections"}, "cv")
    for field in ("name", "label", "email", "phone", "website", "location", "image", "summary"):
        if field in cv and cv[field] is not None and not isinstance(cv[field], str):
            raise ExportError(f"cv.{field}: expected text")
    for field, expected in (("address", dict), ("social_networks", list)):
        if field in cv and cv[field] is not None and not isinstance(cv[field], expected):
            raise ExportError(f"cv.{field}: expected {expected.__name__}")
    result = {"name": text(cv.get("name"), "cv.name")}
    for field in ("label", "email", "phone", "website"):
        if not empty(cv.get(field)):
            result["headline" if field == "label" else field] = text(cv[field], f"cv.{field}")

    location = normalized_location(cv)
    if location:
        result["location"] = location

    if not empty(cv.get("image")):
        image = text(cv["image"], "cv.image")
        if urlsplit(image).scheme in ("http", "https"):
            result["photo"] = image
        else:
            # Website image paths are rooted at the repository, including /assets/.
            root = source_path.parent
            if source_path.parent.name == "_data":
                root = source_path.parent.parent
            else:
                for parent in source_path.parents:
                    if (parent / "_config.yml").is_file():
                        root = parent
                        break
            photo = (root / image.lstrip("/")).resolve()
            if not photo.is_relative_to(root.resolve()) or not photo.is_file():
                raise ExportError(f"cv.image: missing repository image file: {image}")
            result["photo"] = os.path.relpath(photo, output_path.parent)

    if not empty(cv.get("social_networks")):
        if not isinstance(cv["social_networks"], list):
            raise ExportError("cv.social_networks: expected a list")
        result["social_networks"] = []
        for i, item in enumerate(cv["social_networks"]):
            path = f"cv.social_networks[{i}]"
            item = mapping(item, path)
            known_fields(item, {"network", "username"}, path)
            result["social_networks"].append({
                field: text(item.get(field), f"{path}.{field}") for field in ("network", "username")
            })

    sections = mapping(cv.get("sections"), "cv.sections")
    exported_sections = {}
    if not empty(cv.get("summary")):
        if "Summary" in sections:
            raise ExportError("cv.sections.Summary: conflicts with cv.summary")
        exported_sections["Summary"] = [text(cv["summary"], "cv.summary")]
    for name, entries in sections.items():
        text(name, "cv.sections section name")
        path = f"cv.sections.{name}"
        if not isinstance(entries, list):
            raise ExportError(f"{path}: expected a list of homogeneous entries")
        converted = [export_entry(entry, f"{path}[{i}]") for i, entry in enumerate(entries)]
        if len({kind for kind, _ in converted}) > 1:
            raise ExportError(f"{path}: mixed entry types are unsupported")
        if converted:
            exported_sections[name] = [entry for _, entry in converted]
    result["sections"] = exported_sections
    return {"cv": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Website CV YAML (read only)")
    parser.add_argument("--output", required=True, type=Path, help="Separate RenderCV YAML output")
    args = parser.parse_args()
    try:
        source_path = args.input.resolve()
        output_path = args.output.resolve()
        if source_path == output_path or (
            source_path.exists() and output_path.exists() and os.path.samefile(source_path, output_path)
        ):
            raise ExportError("input and output must not be the same file")
        document = yaml.load(source_path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        exported = export_document(document, source_path, output_path)
        serialized = yaml.safe_dump(exported, allow_unicode=True, sort_keys=False, width=100)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8")
    except (ExportError, OSError, UnicodeError, yaml.YAMLError) as error:
        print(f"CV export error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
