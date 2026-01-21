"""
Markdown to Google Docs converter.

Converts markdown syntax to Google Docs API requests for formatting.
"""

import re
from typing import List, Dict, Any, Tuple


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

    # First, insert all the text (with markdown stripped for basic structure)
    # We'll process it line by line to handle paragraph styles and lists
    lines = text.split('\n')

    processed_lines = []
    line_styles = []  # Track what style each line needs
    line_start_indices = []

    for line in lines:
        line_start_indices.append(current_index)

        # Detect line type
        if line.startswith('# '):
            # Heading 1
            clean_line = line[2:] + '\n'
            processed_lines.append(clean_line)
            line_styles.append(('heading', 'HEADING_1'))
            current_index += len(clean_line.encode('utf-16-le')) // 2

        elif line.startswith('## '):
            # Heading 2
            clean_line = line[3:] + '\n'
            processed_lines.append(clean_line)
            line_styles.append(('heading', 'HEADING_2'))
            current_index += len(clean_line.encode('utf-16-le')) // 2

        elif line.startswith('### '):
            # Heading 3
            clean_line = line[4:] + '\n'
            processed_lines.append(clean_line)
            line_styles.append(('heading', 'HEADING_3'))
            current_index += len(clean_line.encode('utf-16-le')) // 2

        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            clean_line = line[2:] + '\n'
            processed_lines.append(clean_line)
            line_styles.append(('bullet', None))
            current_index += len(clean_line.encode('utf-16-le')) // 2

        elif re.match(r'^\d+\.\s', line):
            # Numbered list
            match = re.match(r'^\d+\.\s(.*)$', line)
            clean_line = match.group(1) + '\n'
            processed_lines.append(clean_line)
            line_styles.append(('numbered', None))
            current_index += len(clean_line.encode('utf-16-le')) // 2

        else:
            # Regular paragraph
            clean_line = line + '\n' if line else '\n'
            processed_lines.append(clean_line)
            line_styles.append(('paragraph', None))
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
    # Parse the full text for inline markdown
    inline_formatting_requests = parse_inline_formatting(full_text, start_index)
    requests.extend(inline_formatting_requests)

    total_length = len(full_text.encode('utf-16-le')) // 2
    return requests, total_length


def parse_inline_formatting(text: str, base_index: int) -> List[Dict[str, Any]]:
    """
    Parse inline markdown formatting (bold, italic, code) and generate requests.

    Args:
        text: The plain text (with markdown stripped at paragraph level)
        base_index: Starting index in the document

    Returns:
        List of updateTextStyle requests
    """
    requests = []

    # Pattern for **bold**, *italic*, `code`, ***bold+italic***
    # We need to find these in the original text before it was cleaned

    # For now, let's implement a simpler version that looks for patterns
    # in the text and calculates their positions

    # This is complex because we need to:
    # 1. Find markdown patterns in original
    # 2. Calculate positions in cleaned text
    # 3. Generate formatting requests

    # TODO: Implement inline formatting
    # This requires tracking original positions vs cleaned positions

    return requests


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
