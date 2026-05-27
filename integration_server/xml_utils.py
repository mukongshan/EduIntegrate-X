"""XML 处理工具"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from lxml import etree
import xmltodict


def parse_xml(xml_string: str) -> dict:
    """解析 XML 字符串为字典"""
    try:
        return xmltodict.parse(xml_string, strip_whitespace=True)
    except Exception as e:
        raise ValueError(f"Invalid XML: {str(e)}")


def get_text(obj: dict | Any, key: str, default: str = "") -> str:
    """从字典中获取文本值（嵌套键支持）"""
    if not isinstance(obj, dict):
        return default
    
    # 支持多层路径，例如 "meta.homeCollegeId"
    if "." in key:
        keys = key.split(".")
        current = obj
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                return default
        return str(current) if current is not None else default
    
    value = obj.get(key)
    if value is None:
        return default
    if isinstance(value, dict):
        # 如果是字典，尝试获取文本内容
        return str(value.get("#text", "")) if isinstance(value, dict) else str(value)
    return str(value)


def build_xml_response(code: int, message: str, data: dict = None) -> str:
    """构建标准 XML 响应"""
    if data is None:
        data = {}
    
    response_dict = {
        "Response": {
            "code": str(code),
            "message": message,
            "data": data
        }
    }
    
    return xmltodict.unparse(response_dict, pretty=True)


def build_xml_element(tag_name: str, data: dict) -> str:
    """构建 XML 元素"""
    root = ET.Element(tag_name)
    _dict_to_xml(root, data)
    return ET.tostring(root, encoding="unicode")


def validate_xml_fragment(root_name: str, data: dict, xsd_path: str | Path) -> None:
    """用 XSD 校验接口封装内的核心 XML 片段。"""
    xml_content = xmltodict.unparse({root_name: data}, full_document=False)
    schema_doc = etree.parse(str(xsd_path))
    schema = etree.XMLSchema(schema_doc)
    document = etree.fromstring(xml_content.encode("utf-8"))
    if not schema.validate(document):
        errors = "; ".join(error.message for error in schema.error_log)
        raise ValueError(f"XML schema validation failed: {errors}")


def transform_xml_with_xslt(xml_content: str, xslt_path: str | Path) -> str:
    """使用 XSLT 将 XML 字符串转换为目标结构。"""
    xml_doc = etree.fromstring(xml_content.encode("utf-8"))
    xslt_doc = etree.parse(str(xslt_path))
    transformer = etree.XSLT(xslt_doc)
    result = transformer(xml_doc)
    return str(result)


def _dict_to_xml(parent: ET.Element, data: dict):
    """递归将字典转换为 XML"""
    for key, value in data.items():
        if isinstance(value, dict):
            child = ET.SubElement(parent, key)
            _dict_to_xml(child, value)
        elif isinstance(value, list):
            for item in value:
                child = ET.SubElement(parent, key[:-1] if key.endswith("s") else key)
                if isinstance(item, dict):
                    _dict_to_xml(child, item)
                else:
                    child.text = str(item)
        else:
            child = ET.SubElement(parent, key)
            child.text = str(value) if value is not None else ""


def xml_response(code: int, message: str, data: dict = None):
    """快速构建 XML 响应（用于 FastAPI）"""
    from fastapi.responses import Response
    
    if data is None:
        data = {}
    
    xml_content = build_xml_response(code, message, data)
    return Response(content=xml_content, media_type="application/xml; charset=utf-8")
