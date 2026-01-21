# CLAUDE.md - Context for AI Sessions

This document provides context for Claude (or other AI assistants) working with gdoc-editor. It captures key implementation decisions, API quirks, and recommended usage patterns.

## Project Overview

**Purpose**: Enable Claude Code to programmatically read and edit Google Docs via the Google Docs API.

**Design Philosophy**:
- Low-level, precise operations (character indices, not semantic)
- Claude handles all semantic reasoning (finding sections, determining what to change)
- Tool provides structured data optimized for AI parsing

## Architecture

### Module Structure

```
gdoc/
├── __init__.py       # Package metadata
├── auth.py           # OAuth 2.0 authentication
├── reader.py         # Document fetching and parsing
├── editor.py         # Insert/delete/replace operations
└── cli.py            # Command-line interface
```

### Key Design Decisions

1. **Python over Node/Ruby**: Best Google API client library support, mature ecosystem
2. **CLI-first**: Simple interface, easy to invoke from any environment
3. **JSON output**: Structured format that's trivial for Claude to parse
4. **Index-based operations**: No semantic understanding in the tool itself

## Google Docs API Critical Details

### Index System

**UTF-16 code units** (NOT character count):
- Regular ASCII: 1 index per character
- Emoji/surrogate pairs: 2 indices per character
- Newlines: 1 index (`\n`)
- Document starts at index 1 (index 0 is reserved/implicit)

Example:
```
"Hello👋\n"
 H e l l o 👋  \n
 1 2 3 4 5 6 7 8
```

**CRITICAL**: Always account for surrogate pairs when calculating indices. If you see unexpected offsets, check for emoji or special Unicode characters.

### Document Structure

A document body contains a list of `StructuralElement` objects:
- **Paragraph**: Most common, contains text runs and style
- **Table**: Contains rows/cells (basic support implemented)
- **Section Break**: Page breaks, column breaks, etc.

Each element has:
- `startIndex`: Where the element begins
- `endIndex`: Where the element ends (exclusive)

### Paragraph Elements

Paragraphs contain `ParagraphElement` objects:
- **TextRun**: Contiguous text with uniform styling
- **InlineObjectElement**: Embedded images, etc.

### Heading Detection

Headings are paragraphs with `paragraphStyle.namedStyleType` set to:
- `HEADING_1` through `HEADING_6`
- `TITLE`, `SUBTITLE`

The `reader.py` module maps these to simpler names: `heading1`, `heading2`, etc.

### Batch Operations - CRITICAL ORDERING

**Always order operations by descending index** to avoid offset shifts.

Bad:
```json
[
  {"type": "insert", "startIndex": 10, "text": "A"},
  {"type": "insert", "startIndex": 20, "text": "B"}  // Wrong! Index shifted by insertion at 10
]
```

Good:
```json
[
  {"type": "insert", "startIndex": 20, "text": "B"},  // Higher index first
  {"type": "insert", "startIndex": 10, "text": "A"}
]
```

The `editor.py` module handles this automatically via `execute_operations()`.

## Typical Claude Workflow

### Pattern 1: Update a Section

```bash
# 1. Read the document
gdoc read <doc-id> > doc.json

# 2. Parse JSON to find the section
# (Claude uses the structured content array)

# 3. Calculate the new content and indices

# 4. Replace the section content
gdoc replace <doc-id> <start> <end> "New content"
```

### Pattern 2: Insert After a Heading

```bash
# 1. Find the heading
gdoc find <doc-id> "Background" > section.json

# 2. Extract contentStartIndex from the result

# 3. Insert at that index
gdoc insert <doc-id> <contentStartIndex> "New paragraph\n"
```

### Pattern 3: Batch Edits

When making multiple changes:
1. Read the document once
2. Calculate all edit operations with their indices
3. Create operations JSON file
4. Execute batch operation

```bash
# operations.json
[
  {"type": "replace", "startIndex": 200, "endIndex": 250, "text": "Updated"},
  {"type": "insert", "startIndex": 100, "text": "New section\n"},
  {"type": "delete", "startIndex": 50, "endIndex": 75}
]

gdoc batch <doc-id> operations.json
```

## Common Pitfalls

### 1. Forgetting to Account for Newlines

Each paragraph in Google Docs ends with `\n`. If you want to insert a new paragraph, include the trailing newline:

```bash
# Wrong - will merge with next paragraph
gdoc insert <doc-id> 100 "New paragraph"

# Right - maintains document structure
gdoc insert <doc-id> 100 "New paragraph\n"
```

### 2. Using Stale Indices

After any edit operation, all indices after the edit point may shift. Always:
1. Read the document fresh
2. Calculate indices
3. Execute operations
4. Don't reuse indices from before the edit

### 3. Replacing vs Deleting+Inserting

Use `replace` instead of separate delete+insert when possible:
- `replace` is atomic and handles ordering automatically
- Separate operations require careful index management

### 4. Working with Tables

Tables are complex structures. The current implementation has basic table detection but doesn't parse table contents. For table editing:
1. Read the document to identify table start/end indices
2. Consider replacing the entire table if extensive changes are needed

## Authentication Notes

The tool supports two authentication methods:

### Method 1: Service Account (Recommended)
- Uses a JSON key file (`GOOGLE_SERVICE_ACCOUNT_KEY_FILE` environment variable)
- No browser interaction required
- Perfect for CLI/automation/headless environments
- **Important**: Documents must be explicitly shared with the service account email
- Service account email found in the key JSON file: `client_email` field

**Setup**:
1. Create service account in Google Cloud Console
2. Download JSON key file
3. Set `GOOGLE_SERVICE_ACCOUNT_KEY_FILE=/path/to/key.json`
4. Share documents with the service account email (give Editor access)

### Method 2: OAuth 2.0 Flow
- Uses client ID and secret (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`)
- First run opens browser for user consent
- Credentials saved to `~/.gdoc-credentials.json`
- Refresh tokens used automatically on subsequent runs
- No need to share documents (acts as your user)

**Setup**:
1. Create OAuth credentials in Google Cloud Console
2. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
3. Run any command - browser will open for authentication

### Scopes
Currently uses: `https://www.googleapis.com/auth/documents`

This provides full read/write access. For read-only operations, you could use:
`https://www.googleapis.com/auth/documents.readonly`

### Troubleshooting Auth

**Service Account Issues**:
1. Verify key file path is correct
2. Ensure document is shared with service account email
3. Check service account has Editor (not just Viewer) permissions
4. Verify Google Docs API is enabled in the project

**OAuth Issues**:
1. Check environment variables are set
2. Verify Google Cloud project has Docs API enabled
3. Ensure user is added as test user in OAuth consent screen
4. Try `gdoc logout` and re-authenticate

## Performance Considerations

### Read Operations
- Fast, typically <1 second for normal documents
- Large documents (>100 pages) may take longer
- The API returns the full document structure

### Write Operations
- Batch operations are atomic (all succeed or all fail)
- Multiple separate operations are NOT atomic
- No rate limit issues for normal use
- Consider batching when making 3+ edits

## Future Enhancements

Potential improvements for future iterations:

1. **Formatting Support**: Add bold, italic, links, etc.
2. **Table Parsing**: Full table read/write support
3. **Comments**: Read and create comments
4. **Suggestions**: Work with suggested edits
5. **Named Ranges**: Create bookmarks for easier section references
6. **Incremental Sync**: Track revision IDs to detect external changes

## API Documentation References

- [Google Docs API Overview](https://developers.google.com/workspace/docs/api/how-tos/overview)
- [Document Structure](https://developers.google.com/workspace/docs/api/concepts/structure)
- [Insert/Delete Operations](https://developers.google.com/workspace/docs/api/how-tos/move-text)
- [batchUpdate Reference](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate)

## Example Session Transcript

Here's a typical usage flow:

```bash
# Read the document
$ gdoc read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI
{
  "documentId": "13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI",
  "title": "Technical RFC",
  "content": [
    {"type": "heading1", "text": "Background\n", "startIndex": 1, "endIndex": 12},
    {"type": "paragraph", "text": "Old content here.\n", "startIndex": 12, "endIndex": 30}
  ],
  "totalLength": 30
}

# Find a specific section
$ gdoc find 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI "Background"
{
  "heading": "Background\n",
  "headingStartIndex": 1,
  "headingEndIndex": 12,
  "contentStartIndex": 12,
  "contentEndIndex": 30
}

# Replace the section content
$ gdoc replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 12 30 "Updated content.\n"
{
  "replies": [...]
}
✓ Replaced range [12, 30) with new text
```

## Notes for Claude Code

When you (Claude Code) work with this tool:

1. **Always read before editing**: Parse the JSON to understand structure
2. **Use the `content` array**: It's already structured for you (headings vs paragraphs)
3. **Mind the indices**: They're 0-based UTF-16 code units, starting at 1
4. **Preserve newlines**: Every paragraph should end with `\n`
5. **Batch when possible**: More efficient and atomic
6. **Use dry-run**: Preview changes with `--dry-run` flag when uncertain
7. **The `find` command is your friend**: Quick way to locate sections

## Version History

- **v0.2.0** (2026-01-21): Added service account authentication
  - Service account authentication via JSON key file
  - Automatic detection of authentication method
  - Updated documentation for both auth methods

- **v0.1.0** (2026-01-21): Initial implementation
  - Basic read/insert/delete/replace operations
  - OAuth authentication
  - JSON output format
  - Batch operation support
