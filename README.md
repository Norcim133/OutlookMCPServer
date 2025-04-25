# OutlookMCPServer

This project is an MCP server that gives Claude Desktop access to your Microsoft 365 mail (and soon, calendar) using the Microsoft Graph API.

---

## ✨ Features

- ✅ **Mail access**: Search, filter, and analyze your inbox from Claude or any MCP-compatible agent
- 🔜 **Calendar support**: Planned parity with mail features (querying, filtering, etc.)
- 🚧 **OneDrive support**: Possible future direction after mail and calendar are robust

---

## 🧱 Tech Stack

- [`msgraph`](https://github.com/microsoftgraph/msgraph-sdk-python) (modern Microsoft Graph SDK)
- `azure.identity` with `DeviceCodeCredential` and `TokenCachePersistenceOptions`
- `FastMCP` — simple MCP-compliant server interface
- `uv` — fast Python dependency and env management

---

## ⚙️ Requirements

This is currently built to:

- Run locally on **macOS**
- Be used with **Claude Desktop**
- Authenticate using an **Azure-registered application**

> ⚠️ You must have **admin access to an Azure tenant** to configure this — the app registration requires consent for Microsoft Graph scopes (e.g. `Mail.Read`, `Calendars.Read`), which is **not user-consentable** by default in most orgs.

---

## 🚀 Getting Started

```bash
# Set up the environment
uv venv
uv pip install -r uv.lock

# Run locally using MCP Inspector
uv run mcp dev mcpserver/server.py
```
To integrate with Claude Desktop, add this to your claude_desktop_config.json:
```
{
  "mcpServers": {
    "outlook": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/OutlookMCPServer",
        "run",
        "mcpserver/main.py"
      ]
    }
  }
}
```
Then restart Claude Desktop.

## 🔐 Auth Notes

The first time you run the server, you’ll be prompted to authenticate via a browser window. This uses the Microsoft DeviceCodeCredential flow with local caching, so you’ll only need to sign in once.

---

## 📦 Folder Structure
```
.
├── README.md
├── main.py
├── settings.py
├── auth_cache/
│   └── auth_record.json
├── mcpserver/
│   ├── __init__.py
│   ├── graph.py
│   ├── mail_query.py
│   ├── message_info.py
│   ├── msgraph_client.py
│   └── server.py
├── tests/
```

---

## 📌 Roadmap
- Mail integration
- Calendar integration
- Optional OneDrive integration
- Windows support
- GUI-free auth for end-users (if feasible)

---

## 📄 License
### MIT

Copyright (c) 2024 Enthoosa AI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.