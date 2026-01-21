# gdoc-editor

CLI tool for programmatic Google Docs editing via the Google Docs API. Designed for AI-driven document management, enabling precise read and edit operations on Google Docs.

## Quick Start

```bash
# 1. Install the tool
pipx install git+https://github.com/defaye/gdoc-editor.git

# 2. Add authentication to your shell config (one-time setup)
echo 'export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="$HOME/.config/gdoc-editor-key.json"' >> ~/.zshrc
# or for bash: >> ~/.bashrc

# 3. Reload your shell
source ~/.zshrc

# 4. Use it
gdoc-cli read <document-id>

# Check your version
gdoc-cli --version
```

**Prerequisites**: You need a Google Cloud service account key file. See [Authentication Setup](#authentication-setup) below for how to create one.

## Features

- **Read**: Fetch document content with structural information (headings, paragraphs, indices)
- **Insert**: Insert text at a specific character index
- **Insert Markdown** (NEW!): Insert formatted text using intuitive markdown syntax in one fast operation
- **Delete**: Delete a range of text by start/end indices
- **Replace**: Replace a range with new text
- **Find**: Locate sections by heading text
- **Batch**: Execute multiple operations atomically
- **Dry-run**: Preview changes before applying them

## Installation

### Method 1: pipx (Recommended)

**Best for**: Global installation, use across multiple projects, Claude Code sessions

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments, making them available system-wide without polluting your global Python environment.

```bash
# Install pipx if you don't have it
brew install pipx  # macOS
# or: python3 -m pip install --user pipx

# Install gdoc-editor
pipx install git+https://github.com/defaye/gdoc-editor.git

# Verify installation
gdoc-cli --help
```

The `gdoc-cli` command is now available globally in any terminal or Claude Code session.

**Checking your version:**
```bash
gdoc-cli --version
```

**Updating to the latest version:**
```bash
# Check current version
gdoc-cli --version

# Upgrade
pipx upgrade gdoc-editor

# Verify new version
gdoc-cli --version
```

**Uninstalling:**
```bash
pipx uninstall gdoc-editor
```

### Method 2: pip (System-wide)

**Best for**: Simple installation without pipx

```bash
# Install directly with pip
pip install git+https://github.com/defaye/gdoc-editor.git

# Verify installation
gdoc-cli --help
```

### Method 3: Development Installation

**Best for**: Contributing to the project or making local modifications

```bash
# Clone the repository
git clone https://github.com/defaye/gdoc-editor.git
cd gdoc-editor

# Install in editable mode
pip install -e .

# Changes to the code will be reflected immediately
```

### Prerequisites

- Python 3.8 or higher
- Google Workspace account with access to Google Docs
- Google Cloud project with Docs API enabled (see Authentication Setup below)

## Authentication Setup

This tool supports two authentication methods.

### Quick Links (replace YOUR-PROJECT-ID with your actual project ID)

- **Google Cloud Console**: https://console.cloud.google.com/
- **Enable Google Docs API**: https://console.cloud.google.com/apis/library/docs.googleapis.com?project=YOUR-PROJECT-ID
- **Service Accounts**: https://console.cloud.google.com/iam-admin/serviceaccounts?project=YOUR-PROJECT-ID
- **API Library**: https://console.cloud.google.com/apis/library?project=YOUR-PROJECT-ID

### Method 1: Service Account (Recommended for CLI/Automation)

**Best for**: Programmatic access, automation, CI/CD, no browser required

**Pros**:
- No browser-based OAuth flow
- Works in headless environments
- Simple JSON key file

**Cons**:
- Must explicitly share documents with the service account email

**Setup**:

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Click "Select a project" dropdown (top bar)
   - Click "New Project"
   - Give it a name (e.g., "gdoc-editor")
   - Click "Create"
   - Wait for the project to be created and select it

2. **Enable the Google Docs API**

   **IMPORTANT**: This step is required or you'll get "API not enabled" errors.

   - Direct link: `https://console.cloud.google.com/apis/library/docs.googleapis.com?project=YOUR-PROJECT-ID`
   - Or navigate: From the Cloud Console homepage, go to "APIs & Services" > "Library"
   - Search for "Google Docs API"
   - Click on "Google Docs API"
   - Click the blue "Enable" button
   - Wait a few moments for it to activate

3. **Create a Service Account**

   **Note**: Service Accounts are under IAM & Admin, not under APIs & Services > Credentials.

   - Direct link: `https://console.cloud.google.com/iam-admin/serviceaccounts?project=YOUR-PROJECT-ID`
   - Or navigate: From the Cloud Console, click the hamburger menu (☰) > "IAM & Admin" > "Service Accounts"
   - Click "+ CREATE SERVICE ACCOUNT" (at the top)
   - Give it a name (e.g., "gdoc-editor-bot")
   - Optionally add a description (e.g., "Service account for gdoc-editor CLI tool")
   - Click "CREATE AND CONTINUE"
   - Skip the optional role assignment (click "CONTINUE")
   - Skip granting users access (click "DONE")

4. **Create and Download Key File**
   - You should now see your service account in the list
   - Click on the service account email to open its details
   - Go to the "KEYS" tab (top menu)
   - Click "ADD KEY" > "Create new key"
   - Select "JSON" format
   - Click "CREATE"
   - The key file will download automatically (e.g., `gdoc-editor-1a2b3c4d5e6f.json`)
   - **IMPORTANT**: Keep this file secure - it's like a password for your service account

5. **Configure the Tool** (one-time setup)

   Move the downloaded key file to a permanent location:
   ```bash
   mkdir -p ~/.config
   mv ~/Downloads/gdoc-editor-*.json ~/.config/gdoc-editor-key.json
   ```

   Add the environment variable to your shell config:
   ```bash
   # For zsh (macOS default)
   echo 'export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="$HOME/.config/gdoc-editor-key.json"' >> ~/.zshrc
   source ~/.zshrc

   # For bash (Linux default)
   echo 'export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="$HOME/.config/gdoc-editor-key.json"' >> ~/.bashrc
   source ~/.bashrc
   ```

   Verify it's set:
   ```bash
   echo $GOOGLE_SERVICE_ACCOUNT_KEY_FILE
   # Should output: /Users/you/.config/gdoc-editor-key.json
   ```

6. **Share Documents with the Service Account**

   Find your service account email:
   ```bash
   grep client_email ~/.config/gdoc-editor-key.json
   # Output: "client_email": "gdoc-editor-bot@project-id.iam.gserviceaccount.com"
   ```

   Share your Google Docs with this email:
   - Open your Google Doc
   - Click "Share" button
   - Paste the service account email
   - Give it "Editor" access
   - Click "Send"

Done! The `gdoc-cli` command is now available everywhere, authenticated and ready to use.

### Method 2: OAuth 2.0 (User Credentials)

**Best for**: Personal use, accessing your own documents

**Pros**:
- No need to share documents
- Acts as your user account

**Cons**:
- Requires browser-based OAuth flow on first run
- Not suitable for headless/automation environments

**Setup**:

1. **Create a Google Cloud Project** (same as above)

2. **Enable the Google Docs API** (same as above)

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure the OAuth consent screen:
     - Choose "External" user type
     - Fill in app name and your email
     - Add your email as a test user
     - Add scope: `https://www.googleapis.com/auth/documents`
   - For application type, select "Desktop app"
   - Give it a name (e.g., "gdoc-editor")
   - Click "Create"

4. **Save Your Credentials**
   - Copy the client ID and client secret
   - Set environment variables:
     ```bash
     export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
     export GOOGLE_CLIENT_SECRET="your-client-secret"
     ```
   - Or add to `.env` file:
     ```bash
     cp .env.example .env
     # Edit .env and add your credentials
     ```

5. **First Run Authentication**
   - The first time you run a command, a browser window will open
   - Sign in with your Google account
   - Grant the requested permissions
   - Credentials will be saved to `~/.gdoc-credentials.json` for future use

## Usage

### Read a document

Get the full document structure as JSON:

```bash
gdoc-cli read <document-id>
```

You can use either the document ID or the full URL:

```bash
gdoc-cli read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI
# or
gdoc-cli read https://docs.google.com/document/d/13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI/edit
```

Output format (JSON):
```json
{
  "documentId": "...",
  "title": "Document Title",
  "revisionId": "...",
  "content": [
    {
      "type": "heading1",
      "text": "Introduction\n",
      "startIndex": 1,
      "endIndex": 14
    },
    {
      "type": "paragraph",
      "text": "This is the content...\n",
      "startIndex": 14,
      "endIndex": 37
    }
  ],
  "fullText": "Introduction\nThis is the content...\n",
  "totalLength": 1234
}
```

Get plain text only:
```bash
gdoc-cli read <document-id> --format text
```

### Insert text

Insert text at a specific index:

```bash
gdoc-cli insert <document-id> <index> "Text to insert"
```

Example:
```bash
gdoc-cli insert 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 100 "New paragraph here.\n"
```

**Paragraph styling**: Control the style of inserted text with `--style`:

```bash
# Insert as normal text (auto-applied if text ends with \n)
gdoc-cli insert <document-id> <index> "Normal text.\n" --style NORMAL_TEXT

# Insert as a heading
gdoc-cli insert <document-id> <index> "Section Title\n" --style HEADING_2

# Available styles: NORMAL_TEXT, HEADING_1, HEADING_2, HEADING_3, HEADING_4, HEADING_5, HEADING_6, TITLE, SUBTITLE
```

**Important**: If you insert text ending with `\n` without specifying `--style`, it will automatically be styled as `NORMAL_TEXT` to prevent inheriting incorrect heading formats.

**Bullet and numbered lists**: Create properly formatted lists with `--bullet`:

```bash
# Insert as bulleted list
gdoc-cli insert <document-id> <index> "Item 1\nItem 2\nItem 3\n" --bullet BULLET_DISC_CIRCLE_SQUARE

# Insert as numbered list
gdoc-cli insert <document-id> <index> "Step 1\nStep 2\nStep 3\n" --bullet NUMBERED_DECIMAL_ALPHA_ROMAN

# Available bullet presets:
# - BULLET_DISC_CIRCLE_SQUARE (• ○ ■)
# - BULLET_DIAMONDX_ARROW3D_SQUARE (◆ ✖ ➔)
# - BULLET_CHECKBOX (☐ checkboxes)
# - BULLET_ARROW_DIAMOND_DISC (➔ ◆ •)
# - NUMBERED_DECIMAL_ALPHA_ROMAN (1. a. i.)
# - NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS (1) a) i))
# - NUMBERED_DECIMAL_NESTED (1. 1.1. 1.1.1.)
# - NUMBERED_UPPERALPHA_ALPHA_ROMAN (A. a. i.)
# - NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL (I. A. 1.)
# - NUMBERED_ZERODECIMAL_ALPHA_ROMAN (01. a. i.)
```

**Text formatting**: Apply character-level formatting like bold, italic, etc.:

```bash
# Single formatting
gdoc-cli insert <document-id> <index> "Bold text" --bold
gdoc-cli insert <document-id> <index> "Italic text" --italic
gdoc-cli insert <document-id> <index> "Underlined text" --underline
gdoc-cli insert <document-id> <index> "Strikethrough text" --strikethrough
gdoc-cli insert <document-id> <index> "Code snippet" --code

# Combine multiple formats
gdoc-cli insert <document-id> <index> "Bold and italic" --bold --italic
gdoc-cli insert <document-id> <index> "All formats!" --bold --italic --underline --strikethrough --code

# Available text formats:
# --bold          Make text bold
# --italic        Make text italic
# --underline     Underline text
# --strikethrough Add strikethrough
# --code          Apply monospace font (Courier New) for code
```

**Escape sequences**: The tool automatically converts escape sequences in your text:
```bash
# \n becomes a real newline
gdoc-cli insert <doc-id> 100 "Line 1\nLine 2\n"

# \\ becomes a single backslash
gdoc-cli insert <doc-id> 100 "Path: C:\\Users\\Name\n"
```

**Note**: Google Docs does not visually render tab characters (`\t`), so tab escape sequences are not supported.

Preview without executing:
```bash
gdoc-cli insert <document-id> <index> "Text" --dry-run
```

### Insert markdown (Recommended!)

The fastest and most intuitive way to insert formatted content. Write natural markdown syntax and insert it in a single operation:

```bash
gdoc-cli insert-md <document-id> <index> "# My Heading

This is a paragraph with **bold** and *italic* text.

## Features

- Bullet point 1
- Bullet point 2
- Bullet point 3

### Numbered Lists

1. First item
2. Second item
3. Third item
"
```

**Why use markdown?**
- **Fast**: Single API call instead of multiple operations
- **Intuitive**: Write natural markdown syntax
- **Complete**: Supports headings, lists, and inline formatting
- **Simple**: No index calculations or style flags needed

**Load markdown from a file**:
```bash
gdoc-cli insert-md <document-id> <index> --file content.md
```

**Supported markdown features**:
- Headings: `#`, `##`, `###` (H1, H2, H3)
- Bullet lists: `- item` or `* item`
- Numbered lists: `1. item`, `2. item`
- Bold: `**text**` (coming soon)
- Italic: `*text*` (coming soon)
- Code: `` `text` `` (coming soon)

**Example: Creating a complete document**:
```bash
# Create a full document with one command
gdoc-cli insert-md 1ABC...xyz 1 "# Project Overview

This document outlines our Q1 goals and milestones.

## Goals

- Increase user engagement
- Improve performance
- Launch new features

## Timeline

1. Planning phase (Week 1-2)
2. Development (Week 3-8)
3. Testing and launch (Week 9-10)

## Next Steps

Review this document and provide feedback by EOW.
"
```

**Revision safety**: Works just like regular insert
```bash
# With safety check (default)
gdoc-cli insert-md <document-id> <index> "# Content"

# Skip safety check
gdoc-cli insert-md <document-id> <index> "# Content" --force

# Preview without executing
gdoc-cli insert-md <document-id> <index> "# Content" --dry-run
```

**Pro tip**: For complex documents, use markdown instead of manual insert operations. It's faster, clearer, and less error-prone.

### Delete text

Delete a range of text:

```bash
gdoc-cli delete <document-id> <start-index> <end-index>
```

Example:
```bash
gdoc-cli delete 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 50 75
```

### Replace text

Replace a range with new text:

```bash
gdoc-cli replace <document-id> <start-index> <end-index> "New text"
```

Example:
```bash
gdoc-cli replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 20 45 "Updated content.\n"
```

### Find sections

Locate a section by heading text:

```bash
gdoc-cli find <document-id> "Section Heading"
```

Returns the heading location and section content range:
```json
{
  "heading": "Background\n",
  "headingStartIndex": 100,
  "headingEndIndex": 112,
  "contentStartIndex": 112,
  "contentEndIndex": 450
}
```

### Revision safety checks

By default, all edit operations (insert, delete, replace) include a safety check to prevent overwriting changes made by others:

```bash
# This will fail if the document was modified since you last read it
gdoc-cli insert <document-id> 100 "My text\n"

# Error: "Document was modified since last read. Use --force to bypass this check, or re-read the document."
```

**How it works**:
1. Before editing, the tool reads the document's current revision ID
2. The edit request includes this revision ID as a safety check
3. If someone else modified the document in the meantime, Google Docs API rejects the request
4. You must re-read the document to get updated indices before editing

**Bypass the check** (use with caution):
```bash
# Skip revision check - allows editing even if document changed
gdoc-cli insert <document-id> 100 "My text\n" --force
gdoc-cli delete <document-id> 50 75 --force
gdoc-cli replace <document-id> 20 45 "New text\n" --force
```

**When to use `--force`**:
- You're the only one editing the document
- You're okay with potential conflicts
- You're making non-critical changes

**Best practice**: Always re-read the document after failed edits to get the current state and updated indices.

### Batch operations

Execute multiple operations from a JSON file:

```bash
gdoc-cli batch <document-id> operations.json
```

Example `operations.json`:
```json
[
  {
    "type": "insert",
    "startIndex": 100,
    "text": "New text to insert"
  },
  {
    "type": "delete",
    "startIndex": 50,
    "endIndex": 75
  },
  {
    "type": "replace",
    "startIndex": 20,
    "endIndex": 30,
    "text": "Replacement"
  }
]
```

Operations are automatically ordered by descending index to prevent offset issues.

### Logout

Revoke and delete stored credentials:

```bash
gdoc-cli logout
```

## How Indices Work

Google Docs uses **zero-based UTF-16 code unit indices**:

- Index 0 is before the first character
- Each regular character consumes 1 index
- Emoji and special characters (surrogate pairs) consume 2 indices
- Newlines (`\n`) consume 1 index
- The document always starts with index 1 (index 0 is reserved)

Example:
```
Text: "Hello\nWorld"
       H e l l o \n W o r l d
Index: 1 2 3 4 5 6  7 8 9 10 11 12
```

To insert after "Hello\n": use index 7
To delete "World": use startIndex=7, endIndex=12

## Design Philosophy

This tool is designed for **AI-driven document editing**:

- **Low-level operations**: Works with character indices, not semantic content
- **Claude handles reasoning**: The AI figures out what to edit and where
- **Precise control**: No automatic formatting or "helpful" modifications
- **Structured output**: JSON format optimized for programmatic parsing

## Using with Claude Code

Once you've completed the [installation](#installation) and [authentication setup](#authentication-setup), the `gdoc-cli` command is available in all Claude Code sessions.

If starting a brand new machine or Claude Code session where `gdoc-cli` isn't installed:

```bash
pipx install git+https://github.com/defaye/gdoc-editor.git
```

That's it! Authentication is already configured in your shell config, so it just works.

### Workflow Tips

When using this tool with Claude Code:

1. **Always read first**: Use `gdoc-cli read` to get the current document structure before making edits
2. **Prefer markdown**: Use `insert-md` for formatted content - it's faster and more intuitive than multiple insert operations
3. **Find sections**: Use `gdoc-cli find` to locate specific sections by heading
4. **Calculate indices**: Use the structured JSON output to determine exact indices for edits
5. **Test with dry-run**: Use `--dry-run` to preview operations before executing
6. **Batch when possible**: For operations not supported by markdown, group multiple edits into a single batch operation

### Example: Updating a Section

```bash
# 1. Read the document to get structure
gdoc-cli read <doc-id> | jq . > doc.json

# 2. Find the section you want to update
gdoc-cli find <doc-id> "Background"

# 3. Replace the section content
gdoc-cli replace <doc-id> 335 433 "New background text.\n"
```

## Troubleshooting

### "Google Docs API has not been used in project" or "API not enabled"

This is the most common setup issue.

**Solution**:
1. Go to: `https://console.cloud.google.com/apis/library/docs.googleapis.com?project=YOUR-PROJECT-ID`
2. Click the blue "Enable" button
3. Wait 2-5 minutes for the API to activate
4. Try your command again

**How to verify it's enabled**:
- Go to: `https://console.cloud.google.com/apis/dashboard?project=YOUR-PROJECT-ID`
- You should see "Google Docs API" in the list of enabled APIs

### "The caller does not have permission" (403 error)

**Solution**:
1. Open your service account key JSON file
2. Find the `client_email` field (looks like `name@project-id.iam.gserviceaccount.com`)
3. Open your Google Doc
4. Click "Share" button
5. Paste the service account email
6. Give it "Editor" access (not just "Viewer")
7. Click "Send"

### Can't find Service Accounts in Cloud Console

Service Accounts are NOT under "APIs & Services" > "Credentials".

**Correct location**:
- Direct link: `https://console.cloud.google.com/iam-admin/serviceaccounts`
- Or navigate: Hamburger menu (☰) > "IAM & Admin" > "Service Accounts"

### Service account key file not found

**Error**: `Service account key file not found: /path/to/file.json`

**Solution**:
1. Make sure you've downloaded the JSON key file
2. Verify the path in your environment variable or `.env` file:
   ```bash
   echo $GOOGLE_SERVICE_ACCOUNT_KEY_FILE
   ```
3. Use an absolute path, not a relative one:
   - ✅ Good: `/Users/you/.config/gdoc-key.json`
   - ❌ Bad: `./gdoc-key.json`

### OAuth authentication fails (for OAuth method)

- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set correctly
- Delete `~/.gdoc-credentials.json` and re-authenticate
- Check that you've added your email as a test user in OAuth consent screen
- Verify the Google Docs API is enabled in your Cloud project

### Index out of range

- Use `gdoc-cli read` to check the current document length (`totalLength`)
- Remember indices are 0-based UTF-16 code units
- Account for surrogate pairs (emoji, special characters)

## Development

Run tests (coming soon):
```bash
pytest
```

Format code:
```bash
black gdoc/
```

Lint:
```bash
ruff check gdoc/
```

## License

MIT
