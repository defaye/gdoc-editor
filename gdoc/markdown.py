"""
Markdown to Google Docs converter.

Converts markdown syntax to Google Docs API requests for formatting.
"""

import re
from typing import List, Dict, Any, Tuple


def strip_inline_markdown(text: str) -> Tuple[str, List[Tuple[int, int, str]]]:
    """
    Strip inline markdown and return cleaned text with formatting positions.

    Args:
        text: Text with inline markdown (**, *, `)

    Returns:
        Tuple of (cleaned_text, [(start_pos, end_pos, format_type), ...])
    """
    formats = []
    cleaned = []
    i = 0

    while i < len(text):
        # Check for bold+italic (***text***)
        if i + 3 <= len(text) and text[i:i+3] == '***':
            end = text.find('***', i + 3)
            if end != -1 and end > i + 3:
                content = text[i+3:end]
                start_pos = len(''.join(cleaned))
                cleaned.append(content)
                end_pos = len(''.join(cleaned))
                formats.append((start_pos, end_pos, 'bold_italic'))
                i = end + 3
                continue

        # Check for bold (**text**)
        if i + 2 <= len(text) and text[i:i+2] == '**':
            end = text.find('**', i + 2)
            if end != -1 and end > i + 2:
                content = text[i+2:end]
                start_pos = len(''.join(cleaned))
                cleaned.append(content)
                end_pos = len(''.join(cleaned))
                formats.append((start_pos, end_pos, 'bold'))
                i = end + 2
                continue

        # Check for italic (*text*)
        if text[i] == '*':
            end = text.find('*', i + 1)
            if end != -1 and end > i + 1:
                content = text[i+1:end]
                start_pos = len(''.join(cleaned))
                cleaned.append(content)
                end_pos = len(''.join(cleaned))
                formats.append((start_pos, end_pos, 'italic'))
                i = end + 1
                continue

        # Check for code (`text`)
        if text[i] == '`':
            end = text.find('`', i + 1)
            if end != -1 and end > i + 1:
                content = text[i+1:end]
                start_pos = len(''.join(cleaned))
                cleaned.append(content)
                end_pos = len(''.join(cleaned))
                formats.append((start_pos, end_pos, 'code'))
                i = end + 1
                continue

        # Regular character
        cleaned.append(text[i])
        i += 1

    return ''.join(cleaned), formats


def parse_markdown_to_requests(text: str, start_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse markdown text and generate Google Docs API requests.

    Args:
        text: Markdown-formatted text
        start_index: Starting index in the document

    Returns:
        Tuple of (requests_list, total_text_length)
    """
    requests = []
    current_index = start_index

    # Process line by line to handle paragraph styles and inline formatting
    lines = text.split('\n')

    processed_lines = []
    line_styles = []  # Track what style each line needs
    line_start_indices = []
    all_inline_formats = []  # Track all inline formatting

    for line in lines:
        line_start_indices.append(current_index)

        # Detect line type and strip paragraph-level markdown
        if line.startswith('# '):
            # Heading 1
            line_content = line[2:]
            line_styles.append(('heading', 'HEADING_1'))

        elif line.startswith('## '):
            # Heading 2
            line_content = line[3:]
            line_styles.append(('heading', 'HEADING_2'))

        elif line.startswith('### '):
            # Heading 3
            line_content = line[4:]
            line_styles.append(('heading', 'HEADING_3'))

        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            line_content = line[2:]
            line_styles.append(('bullet', None))

        elif re.match(r'^\d+\.\s', line):
            # Numbered list
            match = re.match(r'^\d+\.\s(.*)$', line)
            line_content = match.group(1)
            line_styles.append(('numbered', None))

        else:
            # Regular paragraph
            line_content = line if line else ''
            line_styles.append(('paragraph', None))

        # Strip inline markdown from this line
        cleaned_line, inline_formats = strip_inline_markdown(line_content)
        clean_line = cleaned_line + '\n'

        # Adjust inline format positions to document positions
        for start_pos, end_pos, format_type in inline_formats:
            doc_start = current_index + start_pos
            doc_end = current_index + end_pos
            all_inline_formats.append((doc_start, doc_end, format_type))

        processed_lines.append(clean_line)
        current_index += len(clean_line.encode('utf-16-le')) // 2

    # Join all processed lines to create the plain text to insert
    full_text = ''.join(processed_lines)

    # Request 1: Insert the plain text
    requests.append({
        "insertText": {
            "location": {"index": start_index},
            "text": full_text
        }
    })

    # Request 2+: Apply paragraph styles
    current_idx = start_index
    bullet_ranges = []
    numbered_ranges = []

    for i, (line, (style_type, style_value)) in enumerate(zip(processed_lines, line_styles)):
        line_length = len(line.encode('utf-16-le')) // 2
        line_end = current_idx + line_length

        if style_type == 'heading' and style_value:
            requests.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": current_idx,
                        "endIndex": line_end
                    },
                    "paragraphStyle": {
                        "namedStyleType": style_value
                    },
                    "fields": "namedStyleType"
                }
            })
        elif style_type == 'bullet':
            bullet_ranges.append((current_idx, line_end))
        elif style_type == 'numbered':
            numbered_ranges.append((current_idx, line_end))

        current_idx = line_end

    # Request 3: Apply bullet formatting to all bullet ranges
    if bullet_ranges:
        for start, end in bullet_ranges:
            requests.append({
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start,
                        "endIndex": end
                    },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                }
            })

    # Request 4: Apply numbered formatting to all numbered ranges
    if numbered_ranges:
        for start, end in numbered_ranges:
            requests.append({
                "createParagraphBullets": {
                    "range": {
                        "startIndex": start,
                        "endIndex": end
                    },
                    "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN"
                }
            })

    # Request 5+: Apply inline formatting (bold, italic, code)
    for start_idx, end_idx, format_type in all_inline_formats:
        if format_type == 'bold':
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {"bold": True},
                    "fields": "bold"
                }
            })
        elif format_type == 'italic':
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {"italic": True},
                    "fields": "italic"
                }
            })
        elif format_type == 'bold_italic':
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {"bold": True, "italic": True},
                    "fields": "bold,italic"
                }
            })
        elif format_type == 'code':
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": "Courier New"},
                        "fontSize": {"magnitude": 10, "unit": "PT"}
                    },
                    "fields": "weightedFontFamily,fontSize"
                }
            })

    total_length = len(full_text.encode('utf-16-le')) // 2
    return requests, total_length


def insert_markdown(
    service,
    document_id: str,
    index: int,
    markdown_text: str,
    required_revision_id: str = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Insert markdown-formatted text into a Google Doc.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        index: The index where text should be inserted
        markdown_text: Markdown-formatted text
        required_revision_id: Optional revision ID for safety
        dry_run: If True, return the request without executing it

    Returns:
        API response or request preview if dry_run=True
    """
    # Parse markdown and generate requests
    requests, total_length = parse_markdown_to_requests(markdown_text, index)

    if dry_run:
        return {
            "dry_run": True,
            "requests": requests,
            "total_length": total_length,
            "writeControl": {"requiredRevisionId": required_revision_id} if required_revision_id else None,
        }

    # Execute batch update
    try:
        body = {"requests": requests}
        if required_revision_id:
            body["writeControl"] = {"requiredRevisionId": required_revision_id}

        response = service.documents().batchUpdate(
            documentId=document_id,
            body=body
        ).execute()
        return response
    except Exception as e:
        error_msg = str(e)
        if "requiredRevisionId" in error_msg or "document has been modified" in error_msg.lower():
            raise Exception(f"Document was modified since last read. Use --force to bypass this check, or re-read the document. Error: {e}")
        raise Exception(f"Insert markdown operation failed: {e}")
