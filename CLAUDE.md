# CLAUDE.md - Context for AI Sessions

> **Note:** This project was developed as an exploration of the Google Docs API and is still in active development. For production use with Claude Code, consider the [Google Docs MCP Server](https://github.com/a-bonus/google-docs-mcp) which provides more comprehensive functionality. This tool is useful for learning and understanding low-level Google Docs API operations.

This document provides context for Claude (or other AI assistants) working with gdoc-editor. It captures key implementation decisions, API quirks, and recommended usage patterns.

## Project Overview

**Purpose**: Enable Claude Code to programmatically read and edit Google Docs via the Google Docs API.

**Design Philosophy**:
- Low-level, precise operations (character indices, not semantic)
- Claude handles all semantic reasoning (finding sections, determining what to change)
- Tool provides structured data optimized for AI parsing

## Quick Setup for New Sessions

If starting a new Claude Code session where `gdoc-cli` isn't available:

```bash
pipx install git+https://github.com/pixielabs/gdoc-editor.git
```

**Authentication**: Should already be configured in the user's shell config (`~/.zshrc` or `~/.bashrc`) with:
```bash
export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="$HOME/.config/gdoc-editor-key.json"
```

If authentication isn't working, check:
1. Is the env var set? `echo $GOOGLE_SERVICE_ACCOUNT_KEY_FILE`
2. Does the key file exist? `ls -l ~/.config/gdoc-editor-key.json`
3. Is the document shared with the service account? `grep client_email ~/.config/gdoc-editor-key.json`

**Important**: Documents must be shared with the service account email (found in the key JSON as `client_email`).

## Working with JSON Output

All `gdoc-cli` commands output JSON for easy parsing. Use `jq` to extract specific fields:

### Common jq Patterns

**Get document length:**
```bash
gdoc-cli read <doc-id> | jq '.totalLength'
```

**List all headings with their indices:**
```bash
gdoc-cli read <doc-id> | jq '.content[] | select(.type | startswith("heading")) | {type, text, startIndex, endIndex}'
```

**Find a specific section by heading text:**
```bash
gdoc-cli read <doc-id> | jq '.content[] | select(.type | startswith("heading")) | select(.text | contains("Introduction"))'
```

**Get just the plain text:**
```bash
gdoc-cli read <doc-id> --format text
# or with jq:
gdoc-cli read <doc-id> | jq -r '.fullText'
```

**List all paragraphs (not headings):**
```bash
gdoc-cli read <doc-id> | jq '.content[] | select(.type == "paragraph") | {text, startIndex, endIndex}'
```

**Get content between specific indices:**
```bash
# Find where "Background" section ends and next section begins
gdoc-cli read <doc-id> | jq '.content[] | select(.startIndex >= 100 and .endIndex <= 500)'
```

**Extract revision ID for safety checks:**
```bash
gdoc-cli read <doc-id> | jq -r '.revisionId'
```

### Workflow Example

```bash
# 1. Read document structure
gdoc-cli read <doc-id> | jq . > doc.json

# 2. Find the "Conclusion" section
jq '.content[] | select(.text | contains("Conclusion"))' doc.json

# 3. Note the endIndex of Conclusion heading (e.g., 450)
# 4. Insert new content right after it
gdoc-cli insert-md <doc-id> 450 "## New Section\n\nContent here."
```

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

## Adding New Features - Checklist

When adding a new feature (like a new flag, command, or capability), update ALL of these locations:

### 1. Core Implementation
- [ ] `gdoc/editor.py` - Add function parameters and implementation logic
- [ ] `gdoc/cli.py` - Add CLI arguments to the argument parser
- [ ] `gdoc/cli.py` - Update handler function (e.g., `handle_insert`) to pass new parameters
- [ ] `gdoc/cli.py` - Update success message to reflect new feature

### 2. CLI Help Text
- [ ] `gdoc/cli.py` - Update `epilog` in `setup_parser()` with examples of new feature
- [ ] `gdoc/cli.py` - Add argument with clear `help` text in subparser
- [ ] `gdoc/cli.py` - Add description to subparser if it affects the command's purpose

### 3. Documentation
- [ ] `README.md` - Add examples in the relevant command section
- [ ] `README.md` - Add feature to the "Features" list at the top if it's major
- [ ] `CLAUDE.md` - Update "When you work with this tool" tips section
- [ ] `CLAUDE.md` - Add entry to "Version History" section

### 4. Version Management
- [ ] `gdoc/__init__.py` - Bump `__version__`
- [ ] `pyproject.toml` - Update `version` field to match

### 5. Testing
- [ ] Test the feature manually with various combinations
- [ ] Test edge cases (empty input, combined with other flags, etc.)
- [ ] Test with test document to verify visual rendering
- [ ] Run `gdoc-cli --help` to verify help text looks correct
- [ ] Run `gdoc-cli <command> --help` to verify subcommand help

### 6. Git Commit
- [ ] Write clear commit message describing the feature
- [ ] Include examples in commit message
- [ ] List all changes (implementation, CLI, docs)
- [ ] Add "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

### Example: Adding Text Formatting (v0.6.0)

This is a good reference for how all pieces fit together:

**Implementation**: Added `bold`, `italic`, etc. parameters to `insert_text()` in editor.py, built `updateTextStyle` request

**CLI**: Added `--bold`, `--italic` flags to insert parser, updated `handle_insert()` to pass them through

**Help**: Added text formatting examples to epilog, clear help text for each flag

**Docs**: Added "Text formatting" section to README with examples, updated CLAUDE.md tips and version history

**Testing**: Tested individually and combined, verified visual rendering in test doc

**Commit**: Detailed commit message with examples, implementation notes, and testing confirmation

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

## CRITICAL: Working with Indices - Common Mistakes

### ❌ **WRONG: Sequential inserts with stale indices**
```bash
# This WILL break - each insert shifts indices!
gdoc-cli insert <doc-id> 100 "Part 1"
gdoc-cli insert <doc-id> 108 "Part 2"  # Wrong! Index 108 moved when we inserted at 100
```

### ❌ **WRONG: Building sentences piecemeal**
```bash
# This is fragile and error-prone
gdoc-cli insert <doc-id> 1 "This text is "
gdoc-cli insert <doc-id> 14 "bold" --bold  # Index 14 is now wrong!
gdoc-cli insert <doc-id> 18 " and more"
```

### ✅ **RIGHT: Complete paragraphs in one operation**
```bash
# Insert complete, self-contained blocks
gdoc-cli insert <doc-id> 1 "This is a complete paragraph.\n"
gdoc-cli insert <doc-id> 1 "Another complete paragraph.\n"  # Pushes first one down
```

### ✅ **RIGHT: Build document from bottom to top**
```bash
# Insert at index 1 repeatedly - each insertion pushes previous content down
gdoc-cli insert <doc-id> 1 "Closing paragraph.\n"
gdoc-cli insert <doc-id> 1 "Middle paragraph.\n"
gdoc-cli insert <doc-id> 1 "Opening paragraph.\n"
# Result: Opening, Middle, Closing (in correct order)
```

### ✅ **RIGHT: Use batch operations for complex documents**
Create `ops.json`:
```json
[
  {"type": "insert", "startIndex": 1, "text": "Paragraph 1\n"},
  {"type": "insert", "startIndex": 1, "text": "Paragraph 2\n"}
]
```
Then: `gdoc-cli batch <doc-id> ops.json`

### ✅ **RIGHT: Read after each edit if you need fresh indices**
```bash
CURRENT_END=$(gdoc-cli read <doc-id> | jq -r '.content[-1].endIndex')
gdoc-cli insert <doc-id> $CURRENT_END "New text\n"
```

### 🎯 **BEST PRACTICES**

1. **Keep it simple**: One paragraph = one insert operation
2. **Avoid mid-sentence formatting changes**: Use complete styled paragraphs
3. **For complex documents**: Use batch operations with a JSON file
4. **Never guess indices**: Always read the document first
5. **Building incrementally?**: Insert at index 1 and build bottom-to-top

## Typical Claude Workflow

### Pattern 1: Update a Section

```bash
# 1. Read the document
gdoc-cli read <doc-id> > doc.json

# 2. Parse JSON to find the section
# (Claude uses the structured content array)

# 3. Calculate the new content and indices

# 4. Replace the section content
gdoc-cli replace <doc-id> <start> <end> "New content"
```

### Pattern 2: Insert After a Heading

```bash
# 1. Find the heading
gdoc-cli find <doc-id> "Background" > section.json

# 2. Extract contentStartIndex from the result

# 3. Insert at that index
gdoc-cli insert <doc-id> <contentStartIndex> "New paragraph\n"
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

gdoc-cli batch <doc-id> operations.json
```

## Common Pitfalls

### 1. Forgetting to Account for Newlines

Each paragraph in Google Docs ends with `\n`. If you want to insert a new paragraph, include the trailing newline:

```bash
# Wrong - will merge with next paragraph
gdoc-cli insert <doc-id> 100 "New paragraph"

# Right - maintains document structure
gdoc-cli insert <doc-id> 100 "New paragraph\n"
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

### 4. Paragraph Style Inheritance

When you insert text, it inherits the style of surrounding text. This can cause inserted normal text to become a heading.

```bash
# Wrong - may inherit HEADING_2 style if inserted after a heading
gdoc-cli insert <doc-id> 100 "Normal text\n"

# Right - explicitly set style to NORMAL_TEXT
gdoc-cli insert <doc-id> 100 "Normal text\n" --style NORMAL_TEXT

# Or insert a heading
gdoc-cli insert <doc-id> 100 "New Section\n" --style HEADING_2
```

**Auto-styling**: If your text ends with `\n` and you don't specify `--style`, `NORMAL_TEXT` is automatically applied to prevent style inheritance issues.

### 5. Working with Tables

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

**Most Common Issue: "API not enabled" (403 error)**
- Direct fix: https://console.cloud.google.com/apis/library/docs.googleapis.com?project=PROJECT-ID
- Enable the Google Docs API
- Wait 2-5 minutes for activation

**Second Most Common: "Permission denied" (403 error)**
- Document not shared with service account email
- Find email in key JSON: `client_email` field
- Share document with this email as Editor (not Viewer)

**Service Account Setup Issues**:
- Service Accounts are under "IAM & Admin" (NOT "APIs & Services")
- Direct link: https://console.cloud.google.com/iam-admin/serviceaccounts
- Key file must use absolute path, not relative

**Service Account Runtime Issues**:
1. Verify key file path is correct: `echo $GOOGLE_SERVICE_ACCOUNT_KEY_FILE`
2. Ensure document is shared with service account email
3. Check service account has Editor (not just Viewer) permissions
4. Verify Google Docs API is enabled in the project

**OAuth Issues**:
1. Check environment variables are set
2. Verify Google Cloud project has Docs API enabled
3. Ensure user is added as test user in OAuth consent screen
4. Try `gdoc-cli logout` and re-authenticate

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
$ gdoc-cli read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI
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
$ gdoc-cli find 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI "Background"
{
  "heading": "Background\n",
  "headingStartIndex": 1,
  "headingEndIndex": 12,
  "contentStartIndex": 12,
  "contentEndIndex": 30
}

# Replace the section content
$ gdoc-cli replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 12 30 "Updated content.\n"
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
5. **Escape sequences work**: Use `\n` for newlines, `\\` for backslashes - they're automatically converted
6. **Use bullets for lists**: Add `--bullet BULLET_DISC_CIRCLE_SQUARE` for proper bullet formatting (not spaces+hyphens!)
7. **Text formatting available**: Use `--bold`, `--italic`, `--code`, etc. for character-level formatting (combinable!)
8. **Revision safety is automatic**: Edits will fail if document was modified since last read (use `--force` to override)
9. **Batch when possible**: More efficient and atomic
10. **Use dry-run**: Preview changes with `--dry-run` flag when uncertain
11. **The `find` command is your friend**: Quick way to locate sections

## Version History

- **v0.6.0** (2026-01-21): Added text formatting support (bold, italic, underline, strikethrough, code)
  - New text formatting flags: `--bold`, `--italic`, `--underline`, `--strikethrough`, `--code`
  - Formats can be combined (e.g., `--bold --italic --code`)
  - Uses `updateTextStyle` API for character-level formatting
  - Code formatting applies Courier New monospace font
  - All formatting applied via single updateTextStyle request

- **v0.5.0** (2026-01-21): Added bullet/numbered list support and revision safety checks
  - New `--bullet` option for insert command with 10 preset styles
  - Proper bullet and numbered list formatting (fixes "spaces with hyphens" issue)
  - Automatic revision safety checks prevent editing stale documents
  - New `--force` flag to bypass revision checks when needed
  - Operations fail with clear error if document was modified since last read

- **v0.4.0** (2026-01-21): Added paragraph styling support and escape sequence handling

- **v0.4.0** (2026-01-21): Added paragraph styling support and escape sequence handling
  - New `--style` option for insert command
  - Supports NORMAL_TEXT, HEADING_1-6, TITLE, SUBTITLE
  - Auto-applies NORMAL_TEXT for text ending with `\n` to prevent style inheritance
  - Fixes issue where inserted text inherits incorrect heading formats
  - Added automatic escape sequence decoding (`\n`, `\\`)
  - Fixes issue where literal `\n` appeared in documents instead of newlines
  - Note: Google Docs does not visually render tabs, so `\t` is not supported

- **v0.3.0** (2026-01-21): Renamed command to `gdoc-cli`
  - Changed command from `gdoc` to `gdoc-cli` for clarity
  - Updated all documentation and examples
  - Breaking change: existing users need to use `gdoc-cli` instead of `gdoc`

- **v0.2.0** (2026-01-21): Added service account authentication
  - Service account authentication via JSON key file
  - Automatic detection of authentication method
  - Updated documentation for both auth methods

- **v0.1.0** (2026-01-21): Initial implementation
  - Basic read/insert/delete/replace operations
  - OAuth authentication
  - JSON output format
  - Batch operation support
