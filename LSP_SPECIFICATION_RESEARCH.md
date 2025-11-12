# LSP Settings Mechanism - Official Specification Research

## Overview

The Language Server Protocol (LSP) provides two distinct mechanisms for passing configuration to language servers:
1. **initializationOptions** - passed during server initialization
2. **workspace/didChangeConfiguration** - sent after initialization for dynamic configuration updates

This document provides the official LSP specification details for each mechanism.

---

## 1. Official LSP Settings Mechanism

### 1.1 InitializeParams and initializationOptions

**Location:** LSP Specification 3.17+ - Initialize Request

The `InitializeParams` interface is the first message sent from client to server. It includes:

```typescript
interface InitializeParams extends WorkDoneProgressParams {
  /**
   * The process Id of the parent process that started the server.
   * Is null if the server was not started by another process.
   * If the parent process is not alive then the server should exit.
   */
  processId: integer | null;

  /**
   * Information about the client
   */
  clientInfo?: ClientInfo;

  /**
   * The rootUri of the workspace. Is null if no folder is open.
   */
  rootUri: DocumentUri | null;

  /**
   * User provided initialization options.
   */
  initializationOptions?: LSPAny;

  /**
   * The capabilities provided by the client (editor or tool)
   */
  capabilities: ClientCapabilities;

  /**
   * The initial trace setting. If omitted trace is disabled ('off').
   */
  trace?: TraceValues;

  /**
   * The workspace folders configured in the client when the server starts.
   */
  workspaceFolders?: WorkspaceFolder[] | null;
}
```

**Key Field: `initializationOptions`**

- **Type:** `LSPAny` (any valid JSON value)
- **Optional:** Yes (marked with `?`)
- **Purpose:** "User provided initialization options"
- **Timing:** Sent once during the initialize request, before the initialized notification
- **Server-Specific:** The content and structure is entirely server-dependent

### 1.2 InitializeParams Field Types

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `processId` | integer \| null | Yes | Parent process ID for lifecycle management |
| `clientInfo` | ClientInfo | No | Information about the client (name, version) |
| `rootUri` | DocumentUri \| null | Yes | Workspace root directory |
| `initializationOptions` | LSPAny | No | Server-specific configuration sent at startup |
| `capabilities` | ClientCapabilities | Yes | Declares what the client supports |
| `trace` | 'off' \| 'messages' \| 'verbose' | No | Logging level for server traces |
| `workspaceFolders` | WorkspaceFolder[] \| null | No | Multiple workspace roots (LSP 3.6+) |

---

## 2. workspace/didChangeConfiguration Notification

### 2.1 Official Specification

**Location:** LSP Specification 3.17+ - Workspace Features

The `workspace/didChangeConfiguration` notification is sent from client to server to inform about configuration changes:

```typescript
interface DidChangeConfigurationParams {
  /**
   * The actual changed settings.
   * This is typically a JSON object with the new settings.
   */
  settings: LSPAny;
}
```

### 2.2 Notification Flow

**Typical Sequence:**

```
1. Client → Server: initialize (with initializationOptions)
   └─ Server responds: InitializeResult

2. Client → Server: initialized notification (empty)
   └─ Server enters ready state

3. Client → Server: workspace/didChangeConfiguration (initial settings)
   └─ Server loads configuration

4. Client → Server: workspace/didChangeConfiguration (on each change)
   └─ Server updates configuration dynamically
```

### 2.3 When Settings Take Effect

**InitializationOptions:**
- Sent during the `initialize` request (step 1 above)
- Takes effect immediately when server processes the initialize request
- Server is NOT yet in ready state (no RPC calls to client yet)
- One-time configuration at startup

**workspace/didChangeConfiguration:**
- Can be sent after the `initialized` notification (step 2+)
- Server is in ready state and can make RPC calls to client
- Takes effect immediately upon notification receipt
- Can be sent multiple times during the session
- Allows dynamic configuration updates without server restart

### 2.4 Configuration Request Pattern

Some servers implement a pull-based model using `workspace/configuration` requests:

```typescript
interface ConfigurationParams {
  items: ConfigurationItem[];
}

interface ConfigurationItem {
  /**
   * The configuration section asked for.
   */
  section?: string;

  /**
   * The resource for which the configuration is requested.
   */
  scopeUri?: string;
}
```

**Flow:**
1. Server sends `workspace/configuration` request to client
2. Client responds with settings matching the requested sections
3. Server uses returned settings for configuration

This allows for workspace/file-scoped configuration.

---

## 3. Command-Line Arguments vs Initialization Options

### 3.1 Comparison Table

| Aspect | Command-Line Args | Initialization Options |
|--------|-------------------|------------------------|
| **Purpose** | Control server process startup | Configure server behavior |
| **When** | Before server starts | During initialize handshake |
| **Protocol** | OS/Shell specific | LSP standard |
| **Example** | `["omnisharp", "--stdio"]` | `{ "enableRoslynAnalyzers": true }` |
| **Scope** | Process-level | Configuration-level |
| **Modifiable** | No (fixed at startup) | Can change via didChangeConfiguration |
| **Spec** | Not LSP-defined | Defined in LSP spec (InitializeParams) |

### 3.2 Examples

**Command-Line Arguments (Neovim config):**
```lua
omnisharp = {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'), '--stdio' },
  -- --stdio tells OmniSharp to use stdin/stdout for communication
}
```

**Initialization Options:**
```lua
omnisharp = {
  init_options = {
    enableRoslynAnalyzers = true,
    organizeImportsOnFormat = true,
    enableImportCompletion = true,
  }
}
```

**Settings (workspace/didChangeConfiguration):**
```lua
omnisharp = {
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,
    }
  }
}
```

---

## 4. Timing and Application of Settings

### 4.1 Complete Timeline

```
T0: Neovim starts
    ├─ Loads LSP config
    └─ Determines what settings to use

T1: Server process starts
    ├─ Command: ["omnisharp", "--stdio"]
    └─ Server enters startup phase

T2: Initialize request sent
    ├─ initializationOptions: { enableRoslynAnalyzers: true, ... }
    ├─ capabilities: { ... }
    ├─ rootUri: "file:///path/to/project"
    └─ Server processes initialize request

T3: Server responds with InitializeResult
    ├─ capabilities: { ... }
    ├─ serverInfo: { ... }
    └─ Neovim saves server capabilities

T4: Initialized notification sent
    ├─ Server marks itself as "initialized"
    └─ Server can now make RPC calls to client

T5: workspace/didChangeConfiguration notification
    ├─ settings: { omnisharp: { enableRoslynAnalyzers: true }, ... }
    └─ Server reloads settings (some servers do this)

T6: (Optional) workspace/configuration request
    ├─ Server: "Give me settings for section: 'omnisharp'"
    ├─ Client responds with settings matching that section
    └─ Server uses pulled settings
```

### 4.2 Setting Application Timing

| Setting Type | When Applied | Can Change | Who Applies |
|--------------|-------------|-----------|------------|
| **Command-line args** | T1 | No | OS shell / process spawning |
| **initializationOptions** | T2 | No | Language server (during init) |
| **workspace/didChangeConfiguration** | T5+ | Yes | Language server (on notification) |
| **workspace/configuration (pulled)** | T5+ | Yes | Language server (on request) |

---

## 5. Alternative Methods to Pass Settings

### 5.1 Configuration Files

Some language servers support reading configuration from files:

```
.editorconfig           (EditorConfig standard)
.eslintrc.json          (ESLint)
tsconfig.json           (TypeScript)
omnisharp.json          (OmniSharp - project root)
pyproject.toml          (Python)
.rubocop.yml            (RuboCop)
```

**Advantage:** Settings persist with the project
**Disadvantage:** Not dynamically updateable during session
**LSP Perspective:** Not part of LSP spec, server-specific

### 5.2 Environment Variables

Some servers accept environment variables:

```bash
OMNISHARP_ROSLYN_ANALYZERS=true
LSP_LOG_LEVEL=debug
```

**Advantage:** Cross-platform way to pass settings
**Disadvantage:** Must be set before server starts
**LSP Perspective:** Not part of LSP spec, server-specific

### 5.3 Neovim-Specific Mechanisms

**init_options (Neovim term for initializationOptions):**
```lua
init_options = {
  -- Server-specific options sent during initialize
}
```

**settings (Neovim term for workspace/didChangeConfiguration values):**
```lua
settings = {
  -- Server-specific options sent via workspace/didChangeConfiguration
}
```

### 5.4 Which Method to Use?

```
Startup-only config        → Use initializationOptions (init_options)
Dynamic/changeable config  → Use workspace/didChangeConfiguration (settings)
Process-level control      → Use command-line arguments (cmd)
Project-persistent         → Use .editorconfig or server-specific files
Environment-dependent      → Use environment variables
```

---

## 6. Specification Links and References

### Official LSP Specifications

1. **LSP 3.17 Specification (Current)**
   - Main: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
   - InitializeParams: Section "Initialize Request"
   - workspace/didChangeConfiguration: Section "Workspace Features"

2. **LSP 3.18 Specification (Latest)**
   - GitHub: https://github.com/Microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.18/specification.md
   - Official: https://microsoft.github.io/language-server-protocol/specifications/specification-current/

3. **LSP 3.14 (Stable Reference)**
   - https://microsoft.github.io/language-server-protocol/specifications/specification-3-14/

### Related Documentation

4. **Neovim LSP Documentation**
   - https://neovim.io/doc/user/lsp.html
   - Includes Lua configuration examples

5. **nvim-lspconfig Documentation**
   - https://github.com/neovim/nvim-lspconfig/blob/master/doc/lspconfig.txt
   - Server-specific configuration examples

6. **Language Server Implementation Guides**
   - Visual Studio Code: https://code.visualstudio.com/api/language-extensions/language-server-extension-guide
   - Sublime Text: https://lsp.readthedocs.io/en/stable/

### Type Definitions

7. **Rust LSP Types (lsp_types crate)**
   - https://docs.rs/lsp-types/latest/lsp_types/struct.InitializeParams.html
   - Full TypeScript definitions for LSP structures

8. **Java LSP4j (Eclipse)**
   - https://javadoc.io/static/org.eclipse.lsp4j/org.eclipse.lsp4j/0.12.0/org/eclipse/lsp4j/InitializeParams.html
   - JSon-RPC bindings for Java

---

## 7. Common Issues and Solutions

### 7.1 Settings Not Taking Effect

**Problem:** Changed configuration but server doesn't reflect it

**Diagnosis:**
1. Are you using `init_options` for dynamic settings? → Should use `settings` instead
2. Did you restart the server? → Try `:LspRestart`
3. Does the server support `workspace/didChangeConfiguration`? → Check server docs

**Solution:**
```lua
-- Wrong (init_options are one-time only):
init_options = { enableRoslynAnalyzers = true }

-- Correct (settings can be dynamic):
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true
  }
}
```

### 7.2 Initialization Options vs Settings

**When to use initializationOptions:**
- Server startup parameters
- One-time only settings
- Options that cannot change during session
- Example: `--language C#`

**When to use settings:**
- Dynamic configuration
- Can change without server restart
- User preferences (formatting, severity, etc.)
- Example: `indent_size = 4`

### 7.3 Workspace Configuration Not Sent

**Problem:** Server requests workspace/configuration but client doesn't respond

**Possible Causes:**
- Client doesn't advertise workspace.configuration capability
- Settings keys don't match server's expectations
- Server section parameter doesn't exist

**Solution:**
- Consult server documentation for exact key names
- Use `:LspInfo` to check client capabilities
- Check Neovim LSP logs for RPC errors

---

## 8. OmniSharp-Specific Settings

Based on the LSP spec, here's how to properly configure OmniSharp:

### 8.1 Initialization Options (init_options)

Sent once during server startup:

```lua
init_options = {
  -- OmniSharp-specific startup parameters
  -- Limited documentation, server-dependent
}
```

### 8.2 Settings (workspace/didChangeConfiguration)

Dynamic settings that OmniSharp reads:

```lua
settings = {
  omnisharp = {
    -- Core settings
    enableRoslynAnalyzers = true,
    enableEditorConfigSupport = true,
    enableReferenceCodeLens = true,

    -- Formatting
    organizeImportsOnFormat = true,
    organize_imports_on_format = true,  -- Alternative key

    -- Code completion
    enableImportCompletion = true,

    -- Paths and locations
    -- (usually determined from rootUri in InitializeParams)

    -- Logging
    loggingLevel = "information",  -- debug, verbose, etc.
  }
}
```

### 8.3 Command-Line Arguments

Passed when starting OmniSharp process:

```lua
cmd = {
  vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
  '--stdio',           -- Use stdin/stdout for LSP communication
  '--languageId',      -- (optional) Language specification
  'csharp',
}
```

---

## 9. Summary

### Key Takeaways

1. **InitializationOptions (`init_options`):**
   - Sent during `initialize` request
   - Server-specific format
   - One-time configuration
   - Cannot be changed after server starts

2. **workspace/didChangeConfiguration (`settings`):**
   - Sent after `initialized` notification
   - Can be sent multiple times
   - Allows dynamic configuration
   - Server may pull config via workspace/configuration request

3. **Command-Line Arguments (`cmd`):**
   - Control process startup behavior
   - OS/shell specific
   - Cannot change during session

4. **Timing is Critical:**
   - Args → Server startup (T1)
   - initializationOptions → Initialize handshake (T2)
   - settings → After initialized notification (T5+)

5. **Check Server Documentation:**
   - Each server defines what settings it accepts
   - No universal standard for setting names
   - Some servers use file-based config as primary method

---

## 10. Testing Configuration

### Verify Settings are Received by Server

```vim
" Check client capabilities
:LspInfo

" View all language server capabilities and what the server supports
" Look for 'workspace' capabilities

" Check Neovim LSP logs
:e $NVIM_LOG_FILE
" or
:!tail -f ~/.local/state/nvim/lsp.log
```

### Debug Configuration Issues

```lua
-- In init.lua, add logging
vim.lsp.set_log_level("debug")

-- Check what settings are being sent
-- Look at LSP logs for "didChangeConfiguration" notifications
```

### Verify Server Received Settings

Some servers provide diagnostic commands:
```
:OmniSharp /checkaliases
:OmniSharp /listapiendpoints
```

(Server-dependent; check server documentation)

---

## References

- **LSP Specification v3.17**: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- **InitializeParams Section**: Initialize Request documentation
- **workspace/didChangeConfiguration**: Workspace Features documentation
- **Neovim LSP Module**: https://neovim.io/doc/user/lsp.html
- **nvim-lspconfig**: https://github.com/neovim/nvim-lspconfig

