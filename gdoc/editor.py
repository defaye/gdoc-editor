"""
Document editing module for Google Docs API.

Handles insert, delete, and replace operations on Google Docs
with proper index management and batch operation support.
"""

from typing import List, Dict, Any, Optional


class EditOperation:
    """Represents a single edit operation."""

    def __init__(self, op_type: str, start_index: int, end_index: Optional[int] = None, text: Optional[str] = None):
        self.op_type = op_type  # "insert", "delete", or "replace"
        self.start_index = start_index
        self.end_index = end_index
        self.text = text

    def to_request(self) -> Dict[str, Any]:
        """Convert to Google Docs API request format."""
        if self.op_type == "insert":
            return {
                "insertText": {
                    "location": {"index": self.start_index},
                    "text": self.text,
                }
            }
        elif self.op_type == "delete":
            return {
                "deleteContentRange": {
                    "range": {
                        "startIndex": self.start_index,
                        "endIndex": self.end_index,
                    }
                }
            }
        else:
            raise ValueError(f"Unknown operation type: {self.op_type}")

    def __repr__(self):
        if self.op_type == "insert":
            return f"Insert '{self.text}' at index {self.start_index}"
        elif self.op_type == "delete":
            return f"Delete range [{self.start_index}, {self.end_index})"
        else:
            return f"Unknown operation: {self.op_type}"


def insert_text(
    service,
    document_id: str,
    index: int,
    text: str,
    paragraph_style: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Insert text at a specific index in the document.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        index: The index where text should be inserted (0-based, UTF-16 code units)
        text: The text to insert
        paragraph_style: Optional paragraph style (e.g., 'NORMAL_TEXT', 'HEADING_1', 'HEADING_2')
        dry_run: If True, return the request without executing it

    Returns:
        API response or request preview if dry_run=True

    Raises:
        Exception: If the operation fails
    """
    # Build requests list
    requests = []

    # First request: insert text
    insert_request = {
        "insertText": {
            "location": {"index": index},
            "text": text,
        }
    }
    requests.append(insert_request)

    # Second request: apply paragraph style if specified
    if paragraph_style:
        # Calculate the range of inserted text
        text_length = len(text.encode('utf-16-le')) // 2  # UTF-16 code units
        end_index = index + text_length

        style_request = {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": index,
                    "endIndex": end_index,
                },
                "paragraphStyle": {
                    "namedStyleType": paragraph_style
                },
                "fields": "namedStyleType"
            }
        }
        requests.append(style_request)

    if dry_run:
        return {
            "dry_run": True,
            "requests": requests,
        }

    # Execute batch update
    try:
        response = service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests}
        ).execute()
        return response
    except Exception as e:
        raise Exception(f"Insert operation failed: {e}")


def delete_text(service, document_id: str, start_index: int, end_index: int, dry_run: bool = False) -> Dict[str, Any]:
    """
    Delete a range of text from the document.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        start_index: Start of range to delete (inclusive, 0-based)
        end_index: End of range to delete (exclusive, 0-based)
        dry_run: If True, return the request without executing it

    Returns:
        API response or request preview if dry_run=True

    Raises:
        Exception: If the operation fails
    """
    if end_index <= start_index:
        raise ValueError(f"end_index ({end_index}) must be greater than start_index ({start_index})")

    operation = EditOperation("delete", start_index, end_index)

    if dry_run:
        return {
            "dry_run": True,
            "operation": str(operation),
            "request": operation.to_request(),
        }

    return execute_operations(service, document_id, [operation])


def replace_text(
    service,
    document_id: str,
    start_index: int,
    end_index: int,
    text: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Replace a range of text with new text.

    This performs a delete followed by an insert, properly ordered.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        start_index: Start of range to replace (inclusive, 0-based)
        end_index: End of range to replace (exclusive, 0-based)
        text: The new text to insert
        dry_run: If True, return the request without executing it

    Returns:
        API response or request preview if dry_run=True

    Raises:
        Exception: If the operation fails
    """
    if end_index <= start_index:
        raise ValueError(f"end_index ({end_index}) must be greater than start_index ({start_index})")

    # Order matters: insert first (at higher index), then delete
    # This prevents the delete from shifting the insert index
    operations = [
        EditOperation("insert", end_index, text=text),
        EditOperation("delete", start_index, end_index),
    ]

    if dry_run:
        return {
            "dry_run": True,
            "operations": [str(op) for op in operations],
            "requests": [op.to_request() for op in operations],
        }

    return execute_operations(service, document_id, operations)


def execute_operations(service, document_id: str, operations: List[EditOperation]) -> Dict[str, Any]:
    """
    Execute a batch of edit operations.

    Operations are automatically ordered by descending index to avoid
    offset shifts during execution.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        operations: List of EditOperation objects

    Returns:
        API response from batchUpdate

    Raises:
        Exception: If the batch operation fails
    """
    if not operations:
        return {"message": "No operations to execute"}

    # Sort operations by descending index to avoid offset issues
    # For operations at the same index, inserts should come before deletes
    sorted_ops = sorted(
        operations,
        key=lambda op: (-op.start_index, 0 if op.op_type == "insert" else 1)
    )

    # Convert to API request format
    requests = [op.to_request() for op in sorted_ops]

    # Execute batch update
    try:
        response = service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests}
        ).execute()
        return response
    except Exception as e:
        raise Exception(f"Batch update failed: {e}")


def batch_edit(
    service,
    document_id: str,
    operations: List[Dict[str, Any]],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute multiple edit operations in a single batch.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document to edit
        operations: List of operation dicts with keys:
            - type: "insert", "delete", or "replace"
            - startIndex: int
            - endIndex: int (for delete/replace)
            - text: str (for insert/replace)
        dry_run: If True, return the request without executing it

    Returns:
        API response or request preview if dry_run=True

    Example:
        operations = [
            {"type": "insert", "startIndex": 100, "text": "New text"},
            {"type": "delete", "startIndex": 50, "endIndex": 60},
            {"type": "replace", "startIndex": 20, "endIndex": 30, "text": "Replacement"},
        ]
    """
    edit_operations = []

    for op_dict in operations:
        op_type = op_dict["type"]
        start_index = op_dict["startIndex"]

        if op_type == "insert":
            edit_operations.append(EditOperation("insert", start_index, text=op_dict["text"]))
        elif op_type == "delete":
            end_index = op_dict["endIndex"]
            edit_operations.append(EditOperation("delete", start_index, end_index))
        elif op_type == "replace":
            end_index = op_dict["endIndex"]
            text = op_dict["text"]
            # Replace is insert + delete
            edit_operations.append(EditOperation("insert", end_index, text=text))
            edit_operations.append(EditOperation("delete", start_index, end_index))
        else:
            raise ValueError(f"Unknown operation type: {op_type}")

    if dry_run:
        return {
            "dry_run": True,
            "operations": [str(op) for op in edit_operations],
            "requests": [op.to_request() for op in edit_operations],
        }

    return execute_operations(service, document_id, edit_operations)
