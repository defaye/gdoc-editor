"""
Document reading module for Google Docs API.

Handles fetching and parsing Google Docs into a structured format
optimized for programmatic analysis and editing.
"""

import json
from typing import Dict, List, Any, Optional


def get_document(service, document_id: str) -> Dict[str, Any]:
    """
    Fetch a Google Doc.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to fetch

    Returns:
        Raw document object from the API

    Raises:
        Exception: If the document cannot be fetched
    """
    try:
        document = service.documents().get(documentId=document_id).execute()
        return document
    except Exception as e:
        raise Exception(f"Failed to fetch document: {e}")


def extract_text_from_element(element: Dict[str, Any]) -> str:
    """
    Extract plain text from a paragraph element.

    Args:
        element: A paragraph element from the document structure

    Returns:
        The text content as a string
    """
    text = ""
    if "textRun" in element:
        text += element["textRun"].get("content", "")
    return text


def get_paragraph_style(paragraph: Dict[str, Any]) -> str:
    """
    Determine the type/style of a paragraph (heading, normal text, etc.).

    Args:
        paragraph: A paragraph object from the document structure

    Returns:
        Style name (e.g., "heading1", "heading2", "paragraph", "title")
    """
    if "paragraphStyle" in paragraph:
        style = paragraph["paragraphStyle"]
        if "namedStyleType" in style:
            style_type = style["namedStyleType"]
            # Map Google Docs style types to simpler names
            style_map = {
                "NORMAL_TEXT": "paragraph",
                "TITLE": "title",
                "SUBTITLE": "subtitle",
                "HEADING_1": "heading1",
                "HEADING_2": "heading2",
                "HEADING_3": "heading3",
                "HEADING_4": "heading4",
                "HEADING_5": "heading5",
                "HEADING_6": "heading6",
            }
            return style_map.get(style_type, "paragraph")
    return "paragraph"


def parse_document_structure(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a Google Doc into a structured format optimized for editing.

    Args:
        document: Raw document object from the API

    Returns:
        Structured document with content array, full text, and metadata
    """
    doc_id = document.get("documentId", "")
    title = document.get("title", "")
    revision_id = document.get("revisionId", "")

    # Extract body content
    body = document.get("body", {})
    content_list = body.get("content", [])

    # Parse structural elements
    structured_content = []
    full_text_parts = []

    for element in content_list:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            start_index = element.get("startIndex")
            end_index = element.get("endIndex")

            # Extract text from all elements in the paragraph
            text = ""
            for para_element in paragraph.get("elements", []):
                text += extract_text_from_element(para_element)

            # Get paragraph style
            style = get_paragraph_style(paragraph)

            # Add to structured content (skip empty paragraphs at doc start/end)
            if text.strip() or start_index > 1:
                structured_content.append({
                    "type": style,
                    "text": text,
                    "startIndex": start_index,
                    "endIndex": end_index,
                })
                full_text_parts.append(text)

        elif "table" in element:
            # Handle tables (basic support)
            start_index = element.get("startIndex")
            end_index = element.get("endIndex")
            structured_content.append({
                "type": "table",
                "text": "[TABLE]",
                "startIndex": start_index,
                "endIndex": end_index,
            })
            full_text_parts.append("[TABLE]\n")

        elif "sectionBreak" in element:
            # Handle section breaks
            start_index = element.get("startIndex")
            end_index = element.get("endIndex")
            structured_content.append({
                "type": "section_break",
                "text": "",
                "startIndex": start_index,
                "endIndex": end_index,
            })

    # Combine full text
    full_text = "".join(full_text_parts)

    # Calculate total document length
    total_length = body.get("content", [{}])[-1].get("endIndex", 0) if body.get("content") else 0

    return {
        "documentId": doc_id,
        "title": title,
        "revisionId": revision_id,
        "content": structured_content,
        "fullText": full_text,
        "totalLength": total_length,
    }


def read_document(service, document_id: str, format: str = "json") -> str:
    """
    Read and format a Google Doc.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to read
        format: Output format ("json" or "text")

    Returns:
        Formatted document content as a string
    """
    document = get_document(service, document_id)
    parsed = parse_document_structure(document)

    if format == "text":
        return parsed["fullText"]
    else:
        return json.dumps(parsed, indent=2)


def find_section(service, document_id: str, heading_text: str) -> Optional[Dict[str, Any]]:
    """
    Find a section in the document by heading text.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document
        heading_text: The heading text to search for

    Returns:
        Section info with startIndex and endIndex, or None if not found
    """
    document = get_document(service, document_id)
    parsed = parse_document_structure(document)

    for i, item in enumerate(parsed["content"]):
        if item["type"].startswith("heading") and heading_text.lower() in item["text"].lower():
            # Find the end of this section (next heading or end of doc)
            section_start = item["endIndex"]
            section_end = parsed["totalLength"]

            for next_item in parsed["content"][i + 1:]:
                if next_item["type"].startswith("heading"):
                    section_end = next_item["startIndex"]
                    break

            return {
                "heading": item["text"].strip(),
                "headingStartIndex": item["startIndex"],
                "headingEndIndex": item["endIndex"],
                "contentStartIndex": section_start,
                "contentEndIndex": section_end,
            }

    return None
