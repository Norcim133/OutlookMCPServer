[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/norcim133-outlookmcpserver-badge.png)](https://mseep.ai/app/norcim133-outlookmcpserver)

# OutlookMCPServer

This project is an MCP server that gives Claude Desktop access to your Microsoft 365 mail, calendar, and (soon) files using the Microsoft Graph API.

---

## ✨ Features

- ✅ **Mail access**: Compose, Respond, Sort, Search, Filter, and Analyze your inbox from Claude or any MCP-compatible agent
- ✅ **Calendar support**: Find invites, List Events, Compose/Update/Send Events
- 🚧 **OneDrive support**: Search files, get file metadata
- 🚧 **Sharepoint support**: Load drives, search files, get file metadata

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

# Clone the repository and navigate to it
```
git clone https://github.com/Norcim133/OutlookMCPServer.git
cd OutlookMCPServer
```

# Set up the environment
```
uv venv
uv sync
```

# Run locally using MCP Inspector
```
mcp dev main.py (expect errors)
```
It is much easier to get things working in the Inspector before trying to debug in Claude.

---

## 🔐 Authentication Setup
Before running the application, you need to set up the following:

1. Create an auth_cache folder in the project root (see note):
```BASH
mkdir -p auth_cache
```

2. Create a .env file in the project root
```bash
touch .env
```
3. Add the following to the .env:
```BASH
echo "AZURE_CLIENT_ID=<your-id-from-Azure-portal-here>" > .env
echo "AZURE_TENANT_ID=<your-id-from-Azure-portal-here>" >> .env
echo "AZURE_GRAPH_SCOPES=User.Read Mail.Read Mail.Send Mail.ReadWrite" >> .env
```
NOTE: Additional .env values required for file services
NOTE: On first run, the application will authenticate using the DeviceCodeCredential flow and will create auth_record.json in the auth_cache folder automatically if successful.

### You must have admin access to an Azure tenant to register an application with these permissions.

---
## Claude for Desktop Integration

To integrate with Claude Desktop, add this to your claude_desktop_config.json:
```
{
  "mcpServers": {
    "outlook": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "azure-identity,mcp[cli],msgraph-core,msgraph-sdk",
        "mcp",
        "run",
        "/absolute/path/to/OutlookMCPServer"
      ]
    }
  }
}
```
In Claude Desktop, you can find the json file by looking in Settings/Developer/Edit Config.

NOTE: You may need to replace "uv" with an absolute reference in "command"

### Restart Claude Desktop each time you make a change to config or to the server code.


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
│   └── graph/
│       ├── __init__.py
│       ├── calendar_service.py
│       ├── controller.py
│       ├── file_service.py
│       ├── mail_service.py
│   ├── __init__.py
│   ├── auth_wrapper.py
│   ├── context_manager.py
│   ├── mail_query.py
│   ├── message_info.py
│   └── server.py
├── tests/
├── .env
├── __init__.py
├── main.py
```

---

## 📌 Roadmap
- Mail integration (DONE)
- Auth in Claude Desktop (DONE)
- Calendar integration (DONE)
- OneDrive integration (PARTIALLY COMPLETE)
- Sharepoint integration (PARTIALLY COMPLETE)
- File parsing for LLM (IN PROGRESS)
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