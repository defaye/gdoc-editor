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
        prog="gdoc",
        description="CLI tool for programmatic Google Docs editing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read a document (outputs JSON)
  gdoc read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI

  # Insert text at index 100
  gdoc insert 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 100 "New text"

  # Delete text from index 50 to 60
  gdoc delete 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 50 60

  # Replace text from index 20 to 30
  gdoc replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 20 30 "Replacement text"

  # Find a section by heading
  gdoc find 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI "Background"

  # Revoke stored credentials
  gdoc logout
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
    insert_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a range of text")
    delete_parser.add_argument("document_id", help="Google Doc ID or full URL")
    delete_parser.add_argument("start_index", type=int, help="Start of range (inclusive)")
    delete_parser.add_argument("end_index", type=int, help="End of range (exclusive)")
    delete_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # Replace command
    replace_parser = subparsers.add_parser("replace", help="Replace a range with new text")
    replace_parser.add_argument("document_id", help="Google Doc ID or full URL")
    replace_parser.add_argument("start_index", type=int, help="Start of range (inclusive)")
    replace_parser.add_argument("end_index", type=int, help="End of range (exclusive)")
    replace_parser.add_argument("text", help="Replacement text")
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


def handle_insert(args, service):
    """Handle the insert command."""
    doc_id = extract_document_id(args.document_id)
    result = insert_text(service, doc_id, args.index, args.text, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        print(f"\n✓ Inserted text at index {args.index}")


def handle_delete(args, service):
    """Handle the delete command."""
    doc_id = extract_document_id(args.document_id)
    result = delete_text(service, doc_id, args.start_index, args.end_index, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if not args.dry_run:
        print(f"\n✓ Deleted range [{args.start_index}, {args.end_index})")


def handle_replace(args, service):
    """Handle the replace command."""
    doc_id = extract_document_id(args.document_id)
    result = replace_text(
        service, doc_id, args.start_index, args.end_index, args.text, dry_run=args.dry_run
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
