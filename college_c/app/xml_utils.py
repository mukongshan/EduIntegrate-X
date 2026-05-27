from __future__ import annotations

import xml.etree.ElementTree as ET

from fastapi import Response


_ITEM_TAGS = {
    "classes": "class",
    "students": "student",
    "choices": "choice",
    "courses": "course",
    "users": "user",
    "enrollments": "enrollment",
    "results": "result",
}


def parse_xml(data: bytes | str) -> ET.Element:
    payload = data.decode("utf-8") if isinstance(data, bytes) else data
    return ET.fromstring(payload)


def get_text(parent: ET.Element | None, path: str, default: str | None = None) -> str | None:
    if parent is None:
        return default
    node = parent.find(path)
    if node is None or node.text is None:
        return default
    value = node.text.strip()
    return value if value else default


def _append_mapping(parent: ET.Element, mapping: dict[str, object]) -> None:
    for key, value in mapping.items():
        if isinstance(value, dict):
            child = ET.SubElement(parent, key)
            _append_mapping(child, value)
        elif isinstance(value, list):
            container = ET.SubElement(parent, key)
            item_tag = _ITEM_TAGS.get(key, key[:-1] if key.endswith("s") else "item")
            for item in value:
                child = ET.SubElement(container, item_tag)
                if isinstance(item, dict):
                    _append_mapping(child, item)
                else:
                    child.text = "" if item is None else str(item)
        else:
            child = ET.SubElement(parent, key)
            child.text = "" if value is None else str(value)


def xml_response(code: int, message: str, data: dict[str, object] | None = None, status_code: int = 200) -> Response:
    root = ET.Element("Response")
    ET.SubElement(root, "code").text = str(code)
    ET.SubElement(root, "message").text = message
    data_el = ET.SubElement(root, "data")
    if data:
        _append_mapping(data_el, data)
    return Response(content=ET.tostring(root, encoding="unicode"), media_type="application/xml", status_code=status_code)
