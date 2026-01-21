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

from gdoc import __version__
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
Basic workflow:
  1. Read the document to get structure and indices
  2. Find sections or calculate target indices
  3. Insert, delete, or replace text at specific indices
  4. Re-read if you need updated indices after edits

Examples:
  # Read a document (always do this first!)
  gdoc-cli read <doc-id>
  gdoc-cli read <doc-id> --format text

  # Find a section by heading
  gdoc-cli find <doc-id> "Background"

  # Insert plain text
  gdoc-cli insert <doc-id> 100 "New paragraph.\\n"

  # Insert with heading style
  gdoc-cli insert <doc-id> 100 "Section Title\\n" --style HEADING_2

  # Insert bullet list (v0.5.0+)
  gdoc-cli insert <doc-id> 100 "Item 1\\nItem 2\\nItem 3\\n" --bullet BULLET_DISC_CIRCLE_SQUARE

  # Insert numbered list (v0.5.0+)
  gdoc-cli insert <doc-id> 100 "Step 1\\nStep 2\\nStep 3\\n" --bullet NUMBERED_DECIMAL_ALPHA_ROMAN

  # Insert with text formatting (v0.6.0+)
  gdoc-cli insert <doc-id> 100 "Bold text" --bold
  gdoc-cli insert <doc-id> 100 "Italic text" --italic
  gdoc-cli insert <doc-id> 100 "Code snippet" --code
  gdoc-cli insert <doc-id> 100 "Bold and italic" --bold --italic
  gdoc-cli insert <doc-id> 100 "All formats!" --bold --italic --underline --strikethrough --code

  # Delete text range
  gdoc-cli delete <doc-id> 50 75

  # Replace text range
  gdoc-cli replace <doc-id> 20 45 "New text here.\\n"

  # Force edit (bypass revision safety check)
  gdoc-cli insert <doc-id> 100 "Text\\n" --force

  # Preview changes without executing
  gdoc-cli insert <doc-id> 100 "Text\\n" --dry-run

  # Revoke stored credentials
  gdoc-cli logout

Safety:
  By default, edits fail if the document was modified since your last read.
  This prevents accidentally overwriting changes. Use --force to bypass.

Bullet presets:
  BULLET_DISC_CIRCLE_SQUARE, BULLET_CHECKBOX, NUMBERED_DECIMAL_ALPHA_ROMAN,
  and 7 others. Use 'gdoc-cli insert --help' for the full list.

More info:
  Full documentation: https://github.com/defaye/gdoc-editor
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"gdoc-cli {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Read command
    read_parser = subparsers.add_parser(
        "read",
        help="Read document structure and content",
        description="Fetch the full document with structure (headings, paragraphs) and character indices"
    )
    read_parser.add_argument("document_id", help="Google Doc ID or full URL")
    read_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format: 'json' for structured data (default), 'text' for plain text",
    )

    # Insert command
    insert_parser = subparsers.add_parser(
        "insert",
        help="Insert text at a specific index",
        description="Insert text at a character index with optional styling and bullet formatting"
    )
    insert_parser.add_argument("document_id", help="Google Doc ID or full URL")
    insert_parser.add_argument("index", type=int, help="Character index where text should be inserted (0-based)")
    insert_parser.add_argument("text", help="Text to insert (use \\n for newlines)")
    insert_parser.add_argument(
        "--style",
        choices=["NORMAL_TEXT", "HEADING_1", "HEADING_2", "HEADING_3", "HEADING_4", "HEADING_5", "HEADING_6", "TITLE", "SUBTITLE"],
        help="Paragraph style (auto-applies NORMAL_TEXT if text ends with \\n)"
    )
    insert_parser.add_argument(
        "--bullet",
        choices=["BULLET_DISC_CIRCLE_SQUARE", "BULLET_DIAMONDX_ARROW3D_SQUARE", "BULLET_CHECKBOX",
                 "BULLET_ARROW_DIAMOND_DISC", "NUMBERED_DECIMAL_ALPHA_ROMAN", "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
                 "NUMBERED_DECIMAL_NESTED", "NUMBERED_UPPERALPHA_ALPHA_ROMAN", "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
                 "NUMBERED_ZERODECIMAL_ALPHA_ROMAN"],
        help="Apply bullet/numbered list formatting to inserted paragraphs"
    )
    insert_parser.add_argument("--bold", action="store_true", help="Make text bold")
    insert_parser.add_argument("--italic", action="store_true", help="Make text italic")
    insert_parser.add_argument("--underline", action="store_true", help="Underline text")
    insert_parser.add_argument("--strikethrough", action="store_true", help="Add strikethrough to text")
    insert_parser.add_argument("--code", action="store_true", help="Apply monospace font for code (Courier New)")
    insert_parser.add_argument("--force", action="store_true", help="Skip revision safety check")
    insert_parser.add_argument("--dry-run", action="store_true", help="Preview the operation without executing")

    # Delete command
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a range of text",
        description="Delete text between start and end indices (start inclusive, end exclusive)"
    )
    delete_parser.add_argument("document_id", help="Google Doc ID or full URL")
    delete_parser.add_argument("start_index", type=int, help="Start of range to delete (inclusive)")
    delete_parser.add_argument("end_index", type=int, help="End of range to delete (exclusive)")
    delete_parser.add_argument("--force", action="store_true", help="Skip revision safety check")
    delete_parser.add_argument("--dry-run", action="store_true", help="Preview the operation without executing")

    # Replace command
    replace_parser = subparsers.add_parser(
        "replace",
        help="Replace a range with new text",
        description="Replace text between start and end indices with new text"
    )
    replace_parser.add_argument("document_id", help="Google Doc ID or full URL")
    replace_parser.add_argument("start_index", type=int, help="Start of range to replace (inclusive)")
    replace_parser.add_argument("end_index", type=int, help="End of range to replace (exclusive)")
    replace_parser.add_argument("text", help="Replacement text (use \\n for newlines)")
    replace_parser.add_argument("--force", action="store_true", help="Skip revision safety check")
    replace_parser.add_argument("--dry-run", action="store_true", help="Preview the operation without executing")

    # Find command
    find_parser = subparsers.add_parser(
        "find",
        help="Find a section by heading text",
        description="Locate a section by its heading and return the heading and content ranges"
    )
    find_parser.add_argument("document_id", help="Google Doc ID or full URL")
    find_parser.add_argument("heading", help="Heading text to search for (partial match supported)")

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Execute multiple operations from JSON file",
        description="Run multiple insert/delete/replace operations atomically from a JSON file"
    )
    batch_parser.add_argument("document_id", help="Google Doc ID or full URL")
    batch_parser.add_argument("operations_file", help="Path to JSON file with operations array")
    batch_parser.add_argument("--dry-run", action="store_true", help="Preview the operations without executing")

    # Logout command
    subparsers.add_parser(
        "logout",
        help="Revoke and delete stored credentials",
        description="Remove stored OAuth credentials (service account keys are not affected)"
    )

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
        bold=args.bold,
        italic=args.italic,
        underline=args.underline,
        strikethrough=args.strikethrough,
        code=args.code,
        required_revision_id=revision_id,
        dry_run=args.dry_run
    )
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        style_msg = f" with style {paragraph_style}" if paragraph_style else ""
        bullet_msg = f" as {args.bullet} list" if args.bullet else ""

        # Build text formatting message
        format_parts = []
        if args.bold:
            format_parts.append("bold")
        if args.italic:
            format_parts.append("italic")
        if args.underline:
            format_parts.append("underline")
        if args.strikethrough:
            format_parts.append("strikethrough")
        if args.code:
            format_parts.append("code")

        format_msg = f" ({', '.join(format_parts)})" if format_parts else ""

        print(f"\n✓ Inserted text at index {args.index}{style_msg}{bullet_msg}{format_msg}")


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
