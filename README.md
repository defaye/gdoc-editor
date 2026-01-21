# gdoc-editor

CLI tool for programmatic Google Docs editing via the Google Docs API. Designed for AI-driven document management, enabling precise read and edit operations on Google Docs.

## Features

- **Read**: Fetch document content with structural information (headings, paragraphs, indices)
- **Insert**: Insert text at a specific character index
- **Delete**: Delete a range of text by start/end indices
- **Replace**: Replace a range with new text
- **Find**: Locate sections by heading text
- **Batch**: Execute multiple operations atomically
- **Dry-run**: Preview changes before applying them

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Workspace account with access to Google Docs
- Google Cloud project with Docs API enabled

### Setup

1. Clone this repository:
```bash
cd gdoc-editor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the CLI tool:
```bash
pip install -e .
```

4. Set up Google authentication (see next section)

## Authentication Setup

This tool supports two authentication methods:

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
   - Create a new project or select an existing one

2. **Enable the Google Docs API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Docs API"
   - Click "Enable"

3. **Create a Service Account**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name (e.g., "gdoc-editor-bot")
   - Click "Create and Continue"
   - Skip the optional role assignment (click "Continue")
   - Click "Done"

4. **Create and Download Key File**
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Click "Create" (the key file will download automatically)

5. **Configure the Tool**
   - Save the key file somewhere secure (e.g., `~/.config/gdoc-editor-key.json`)
   - Set the environment variable:
     ```bash
     export GOOGLE_SERVICE_ACCOUNT_KEY_FILE="$HOME/.config/gdoc-editor-key.json"
     ```
   - Or add to `.env` file:
     ```bash
     cp .env.example .env
     # Edit .env and add:
     GOOGLE_SERVICE_ACCOUNT_KEY_FILE=/path/to/your-key.json
     ```

6. **Share Documents with the Service Account**
   - Open the key JSON file and copy the `client_email` (looks like `gdoc-editor-bot@project-id.iam.gserviceaccount.com`)
   - Share your Google Doc with this email address (just like sharing with a person)
   - Give it "Editor" access

That's it! The tool will now authenticate automatically without any browser prompts.

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
gdoc read <document-id>
```

You can use either the document ID or the full URL:

```bash
gdoc read 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI
# or
gdoc read https://docs.google.com/document/d/13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI/edit
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
gdoc read <document-id> --format text
```

### Insert text

Insert text at a specific index:

```bash
gdoc insert <document-id> <index> "Text to insert"
```

Example:
```bash
gdoc insert 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 100 "New paragraph here.\n"
```

Preview without executing:
```bash
gdoc insert <document-id> <index> "Text" --dry-run
```

### Delete text

Delete a range of text:

```bash
gdoc delete <document-id> <start-index> <end-index>
```

Example:
```bash
gdoc delete 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 50 75
```

### Replace text

Replace a range with new text:

```bash
gdoc replace <document-id> <start-index> <end-index> "New text"
```

Example:
```bash
gdoc replace 13WmtU1Q_rE55S8JcBFbq-VG2ySzjg1lrSOjSLjpJoEI 20 45 "Updated content.\n"
```

### Find sections

Locate a section by heading text:

```bash
gdoc find <document-id> "Section Heading"
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

### Batch operations

Execute multiple operations from a JSON file:

```bash
gdoc batch <document-id> operations.json
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
gdoc logout
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

## Tips for Claude Code

When using this tool with Claude Code:

1. **Always read first**: Use `gdoc read` to get the current document structure before making edits
2. **Find sections**: Use `gdoc find` to locate specific sections by heading
3. **Calculate indices**: Use the structured JSON output to determine exact indices for edits
4. **Test with dry-run**: Use `--dry-run` to preview operations before executing
5. **Batch when possible**: Group multiple edits into a single batch operation for atomicity

## Troubleshooting

### Authentication fails

- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set correctly
- Delete `~/.gdoc-credentials.json` and re-authenticate
- Check that you've added your email as a test user in OAuth consent screen
- Verify the Google Docs API is enabled in your Cloud project

### Permission denied on document

- Ensure your Google account has edit access to the document
- For read-only operations, make sure the document is at least viewable

### Index out of range

- Use `gdoc read` to check the current document length (`totalLength`)
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
