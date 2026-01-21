"""
CLI interface for gdoc-editor.

Provides command-line access to Google Docs reading and editing operations.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from gdoc.auth import get_docs_service, revoke_credentials, AuthenticationError
from gdoc.reader import read_document, find_section
from gdoc.editor import insert_text, delete_text, replace_text, batch_edit


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="gdoc-cli",
        description="CLI tool for programmatic Google Docs editing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read a document (outputs JSON)
  gdoc-cli read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI

  # Insert text at index 100
  gdoc-cli insert 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 100 "New text"

  # Insert text with specific paragraph style
  gdoc-cli insert 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 100 "New heading\n" --style HEADING_2

  # Delete text from index 50 to 60
  gdoc-cli delete 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 50 60

  # Replace text from index 20 to 30
  gdoc-cli replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 20 30 "Replacement text"

  # Find a section by heading
  gdoc-cli find 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI "Background"

  # Revoke stored credentials
  gdoc-cli logout
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read a Google Doc")
    read_parser.add_argument("document_id", help="Google Doc ID or full URL")
    read_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    # Insert command
    insert_parser = subparsers.add_parser("insert", help="Insert text at a specific index")
    insert_parser.add_argument("document_id", help="Google Doc ID or full URL")
    insert_parser.add_argument("index", type=int, help="Index where text should be inserted")
    insert_parser.add_argument("text", help="Text to insert")
    insert_parser.add_argument(
        "--style",
        choices=["NORMAL_TEXT", "HEADING_1", "HEADING_2", "HEADING_3", "HEADING_4", "HEADING_5", "HEADING_6", "TITLE", "SUBTITLE"],
        help="Paragraph style (default: NORMAL_TEXT if text ends with newline)"
    )
    insert_parser.add_argument(
        "--bullet",
        choices=["BULLET_DISC_CIRCLE_SQUARE", "BULLET_DIAMONDX_ARROW3D_SQUARE", "BULLET_CHECKBOX",
                 "BULLET_ARROW_DIAMOND_DISC", "NUMBERED_DECIMAL_ALPHA_ROMAN", "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
                 "NUMBERED_DECIMAL_NESTED", "NUMBERED_UPPERALPHA_ALPHA_ROMAN", "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
                 "NUMBERED_ZERODECIMAL_ALPHA_ROMAN"],
        help="Bullet list preset (converts paragraph(s) to bulleted list)"
    )
    insert_parser.add_argument("--force", action="store_true", help="Skip revision safety check (allow editing modified documents)")
    insert_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a range of text")
    delete_parser.add_argument("document_id", help="Google Doc ID or full URL")
    delete_parser.add_argument("start_index", type=int, help="Start of range (inclusive)")
    delete_parser.add_argument("end_index", type=int, help="End of range (exclusive)")
    delete_parser.add_argument("--force", action="store_true", help="Skip revision safety check (allow editing modified documents)")
    delete_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Replace command
    replace_parser = subparsers.add_parser("replace", help="Replace a range with new text")
    replace_parser.add_argument("document_id", help="Google Doc ID or full URL")
    replace_parser.add_argument("start_index", type=int, help="Start of range (inclusive)")
    replace_parser.add_argument("end_index", type=int, help="End of range (exclusive)")
    replace_parser.add_argument("text", help="Replacement text")
    replace_parser.add_argument("--force", action="store_true", help="Skip revision safety check (allow editing modified documents)")
    replace_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Find command
    find_parser = subparsers.add_parser("find", help="Find a section by heading text")
    find_parser.add_argument("document_id", help="Google Doc ID or full URL")
    find_parser.add_argument("heading", help="Heading text to search for")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Execute multiple operations from JSON file")
    batch_parser.add_argument("document_id", help="Google Doc ID or full URL")
    batch_parser.add_argument("operations_file", help="Path to JSON file with operations")
    batch_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Logout command
    subparsers.add_parser("logout", help="Revoke and delete stored credentials")

    return parser


def extract_document_id(doc_id_or_url: str) -> str:
    """
    Extract document ID from a full Google Docs URL or return the ID directly.

    Args:
        doc_id_or_url: Document ID or full URL

    Returns:
        Document ID
    """
    if "docs.google.com" in doc_id_or_url:
        # Extract ID from URL like: https://docs.google.com/document/d/DOC_ID/edit
        parts = doc_id_or_url.split("/")
        if "d" in parts:
            id_index = parts.index("d") + 1
            if id_index < len(parts):
                return parts[id_index]
    return doc_id_or_url


def handle_read(args, service):
    """Handle the read command."""
    doc_id = extract_document_id(args.document_id)
    output = read_document(service, doc_id, format=args.format)
    print(output)


def get_revision_id(service, document_id: str) -> str:
    """
    Get the current revision ID of a document.

    Args:
        service: Authenticated Google Docs API service
        document_id: The ID of the document

    Returns:
        The document's current revision ID
    """
    try:
        doc = service.documents().get(documentId=document_id, fields="revisionId").execute()
        return doc.get("revisionId")
    except Exception as e:
        # If we can't get revision ID, return None (will skip safety check)
        print(f"Warning: Could not get revision ID: {e}", file=sys.stderr)
        return None


def decode_escape_sequences(text: str) -> str:
    """
    Decode escape sequences like \\n and \\\\.

    Handles the case where bash passes literal backslash-n instead of a newline.
    Processes escape sequences in the correct order to handle escaped backslashes.

    Note: Google Docs does not visually render tab characters, so \\t is not supported.
    """
    # Process escape sequences in order (escaped backslashes first)
    replacements = [
        ('\\\\', '\x00'),  # Temporarily replace \\\\ with null byte
        ('\\n', '\n'),     # Replace \\n with newline
        ('\x00', '\\'),    # Restore single backslashes
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def handle_insert(args, service):
    """Handle the insert command."""
    doc_id = extract_document_id(args.document_id)

    # Decode escape sequences (e.g., convert literal \\n to actual newline)
    text = decode_escape_sequences(args.text)

    # Auto-apply NORMAL_TEXT style if text ends with newline and no style specified
    paragraph_style = args.style
    if paragraph_style is None and text.endswith('\n'):
        paragraph_style = 'NORMAL_TEXT'

    # Get revision ID for safety check (unless --force is used)
    revision_id = None
    if not args.force and not args.dry_run:
        revision_id = get_revision_id(service, doc_id)

    result = insert_text(
        service,
        doc_id,
        args.index,
        text,
        paragraph_style=paragraph_style,
        bullet_preset=args.bullet,
        required_revision_id=revision_id,
        dry_run=args.dry_run
    )
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        style_msg = f" with style {paragraph_style}" if paragraph_style else ""
        bullet_msg = f" as {args.bullet} list" if args.bullet else ""
        print(f"\n✓ Inserted text at index {args.index}{style_msg}{bullet_msg}")


def handle_delete(args, service):
    """Handle the delete command."""
    doc_id = extract_document_id(args.document_id)

    # Get revision ID for safety check (unless --force is used)
    revision_id = None
    if not args.force and not args.dry_run:
        revision_id = get_revision_id(service, doc_id)

    result = delete_text(
        service,
        doc_id,
        args.start_index,
        args.end_index,
        required_revision_id=revision_id,
        dry_run=args.dry_run
    )
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        print(f"\n✓ Deleted range [{args.start_index}, {args.end_index})")


def handle_replace(args, service):
    """Handle the replace command."""
    doc_id = extract_document_id(args.document_id)

    # Decode escape sequences (e.g., convert literal \\n to actual newline)
    text = decode_escape_sequences(args.text)

    # Get revision ID for safety check (unless --force is used)
    revision_id = None
    if not args.force and not args.dry_run:
        revision_id = get_revision_id(service, doc_id)

    result = replace_text(
        service,
        doc_id,
        args.start_index,
        args.end_index,
        text,
        required_revision_id=revision_id,
        dry_run=args.dry_run
    )
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        print(f"\n✓ Replaced range [{args.start_index}, {args.end_index}) with new text")


def handle_find(args, service):
    """Handle the find command."""
    doc_id = extract_document_id(args.document_id)
    result = find_section(service, doc_id, args.heading)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print(f"Section with heading '{args.heading}' not found", file=sys.stderr)
        sys.exit(1)


def handle_batch(args, service):
    """Handle the batch command."""
    doc_id = extract_document_id(args.document_id)

    # Load operations from JSON file
    try:
        with open(args.operations_file, "r") as f:
            operations = json.load(f)
    except Exception as e:
        print(f"Error loading operations file: {e}", file=sys.stderr)
        sys.exit(1)

    result = batch_edit(service, doc_id, operations, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        print(f"\n✓ Executed {len(operations)} operations")


def handle_logout(args):
    """Handle the logout command."""
    revoke_credentials()


def main():
    """Main CLI entry point."""
    # Load environment variables from .env file
    load_dotenv()

    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle logout separately (doesn't need API service)
    if args.command == "logout":
        handle_logout(args)
        return

    # Get authenticated service
    try:
        service = get_docs_service()
    except AuthenticationError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing service: {e}", file=sys.stderr)
        sys.exit(1)

    # Route to command handlers
    try:
        if args.command == "read":
            handle_read(args, service)
        elif args.command == "insert":
            handle_insert(args, service)
        elif args.command == "delete":
            handle_delete(args, service)
        elif args.command == "replace":
            handle_replace(args, service)
        elif args.command == "find":
            handle_find(args, service)
        elif args.command == "batch":
            handle_batch(args, service)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
