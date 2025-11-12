# LSP Settings Timing Diagram and Flow

## Complete LSP Initialization and Settings Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEOVIM LSP INITIALIZATION SEQUENCE                        │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: SERVER STARTUP (T0-T1)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       │  Read config from init.lua                 │
       │  - cmd = ["omnisharp", "--stdio"]         │
       │  - init_options = {...}                    │
       │  - settings = {...}                        │
       ├──────────────────────────────────────────→ │ [SPAWN PROCESS]
       │     Spawn with args: ["omnisharp", "--stdio"]
       │                                       └──────────────────┐
       │                                       T0: Server starts   │
       │                                          Awaits init      │
       │                                       <──────────────────┘
       │                                             ✓
       │ [Server now listening on stdin/stdout]     │
       │                                             │

PHASE 2: INITIALIZE HANDSHAKE (T2)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       ├─── Initialize Request ────────────────────→ │
       │  {                                          │
       │    jsonrpc: "2.0",                         │
       │    id: 1,                                  │
       │    method: "initialize",                   │
       │    params: {                                │
       │      processId: 12345,                     │
       │      rootUri: "file:///path/to/project",  │
       │      capabilities: {                        │
       │        textDocument: {...},                 │
       │        workspace: {                         │
       │          didChangeConfiguration: {          │
       │            dynamicRegistration: true       │
       │          }                                  │
       │        }                                    │
       │      },                                     │
       │      initializationOptions: {               │
       │        enableRoslynAnalyzers: true,        │
       │        organizeImportsOnFormat: true,      │
       │        enableImportCompletion: true        │
       │      }  ◄──────────────────────────────    │
       │    }                    These are sent here │
       │  }                                          │
       │                                       ┌────────────────────┐
       │                                       │ T2: Server receives │
       │                                       │ initializationOptions
       │                                       │
       │                                       │ Server loads and    │
       │                                       │ applies these       │
       │                                       │ settings            │
       │                                       └────────────────────┘
       │  ←─── Initialize Response ───────────────┤
       │  {                                   │
       │    jsonrpc: "2.0",                   │
       │    id: 1,                            │
       │    result: {                         │
       │      capabilities: {                 │
       │        textDocumentSync: 1,          │
       │        definitionProvider: true,     │
       │        referencesProvider: true,     │
       │        ...                           │
       │      },                              │
       │      serverInfo: {                   │
       │        name: "OmniSharp",            │
       │        version: "1.x.x"              │
       │      }                               │
       │    }                                 │
       │  }                                   │
       │                                      │

PHASE 3: SERVER READY (T4)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       ├──→ Initialized Notification ───────────────→ │
       │  {                                      ┌───┴────────────────┐
       │    jsonrpc: "2.0",                      │ T4: Server ready   │
       │    method: "initialized",               │ Can now make RPC   │
       │    params: {}                           │ calls to client    │
       │  }                                      └────────────────────┘
       │                                             │

PHASE 4: CONFIGURATION (T5+)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       ├──→ workspace/didChangeConfiguration ──────→ │
       │  Notification                              │
       │  {                                      ┌───┴────────────────┐
       │    jsonrpc: "2.0",                      │ T5: Server receives│
       │    method: "workspace/didChangeConfiguration"
       │    params: {                            │ Dynamic settings   │
       │      settings: {                        │ (can change them)  │
       │        omnisharp: {                     │
       │          enableRoslynAnalyzers: true,   │ Some servers pull  │
       │          organizeImportsOnFormat: true, │ config here via    │
       │          enableImportCompletion: true   │ workspace/config   │
       │        },                               │ request            │
       │        ...other settings...             │
       │      }                                  │
       │    }                                    │
       │  }  ◄───────────────────────────────── │
       │      These settings are sent here      │
       │                                         └────────────────────┘
       │                                             │
       │                                             │
       │  (Optional - Server-initiated)             │
       │  ←──── workspace/configuration ────────────┤
       │  Request                                    │
       │  {                                          │
       │    jsonrpc: "2.0",                         │
       │    id: 42,                                 │
       │    method: "workspace/configuration",     │
       │    params: {                               │
       │      items: [                              │
       │        { section: "omnisharp" }            │
       │      ]                                     │
       │    }                                       │
       │  }                                         │
       │  ──→ workspace/configuration Response ────→│
       │  {                                         │
       │    jsonrpc: "2.0",                        │
       │    id: 42,                                │
       │    result: [                              │
       │      { enableRoslynAnalyzers: true, ... }│
       │    ]                                      │
       │  }                                        │
       │                                            │

PHASE 5: NORMAL OPERATION (T6+)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       ├──→ textDocument/didOpen                ───→ │
       ├──→ textDocument/didChange              ───→ │
       ├──→ textDocument/completion             ───→ │
       │  ←── various responses ──────────────────┤ │
       │                                             │
       │  [Normal LSP operations]                   │
       │                                             │
       ├──→ workspace/didChangeConfiguration ──────→ │
       │  (if settings change, e.g., user changes   │
       │   formatter settings in config)            │
       │                                             │

PHASE 6: SHUTDOWN (T∞)
═══════════════════════════════════════════════════════════════════════════════

    Neovim                                    OmniSharp Server
       │                                             │
       ├──→ shutdown Request                   ───→ │
       │  {                                         │
       │    jsonrpc: "2.0",                        │
       │    id: 999,                               │
       │    method: "shutdown"                     │
       │  }                                     ┌───┴────────────────┐
       │  ←── shutdown Response                 │ T∞: Shutdown     │
       │  {                                     │ sequence starts  │
       │    jsonrpc: "2.0",                     │                  │
       │    id: 999,                            └──────────────────┘
       │    result: null                            │
       │  }                                         │
       │                                            │
       ├──→ exit Notification                   ───→│
       │  {                                    ┌────┴───────────────┐
       │    jsonrpc: "2.0",                    │ T∞+ε: Server       │
       │    method: "exit"                     │ terminates         │
       │  }                                    └───────────────────┘
       │                                             │
```

---

## Settings Application Timeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      SETTINGS APPLICATION TIMELINE                            │
└──────────────────────────────────────────────────────────────────────────────┘

TIME  EVENT                           APPLICABLE TO           STATUS
────  ─────────────────────────────   ─────────────────────   ──────────────────
T0    Server process spawned          cmd args                ✓ Applied
      Example: ["omnisharp", "--stdio"]

T1    Server starts, awaits init      (cmd still running)     ✓ Applied

T2    Initialize request sent         initializationOptions   ─ Not yet sent
      (only to server, not applied)   (init_options)

T2.5  Server processes initialize     initializationOptions   ✓ Applied
      and loads initializationOptions (init_options)

T3    Initialize response received    capabilities            ✓ Stored
      from server

T4    Initialized notification sent   ready state             ✓ Active

T5    workspace/didChangeConfiguration settings              ─ Not yet sent
      notification sent (initial)     (settings)

T5.5  Server processes                settings               ✓ Applied
      didChangeConfiguration          (settings)

T6+   Normal operation                (all settings active)   ✓ Active

T6.1  User changes config in LSP      settings               ─ Not yet applied
      (new Neovim session)            (settings)

T6.2  workspace/didChangeConfiguration settings              ✓ Applied
      sent with new values

T∞    Shutdown sequence               all services           ✗ Inactive
      Server receives shutdown/exit


WHEN EACH SETTING TYPE TAKES EFFECT:

┌──────────────────────────────┬────────────────────┬──────────────────────────┐
│ Setting Type                 │ Applied At         │ Can Change After?        │
├──────────────────────────────┼────────────────────┼──────────────────────────┤
│ cmd args                     │ T0 (process spawn) │ No (process already      │
│ Example: --stdio             │                    │ started)                 │
├──────────────────────────────┼────────────────────┼──────────────────────────┤
│ initializationOptions        │ T2.5               │ No (only sent once       │
│ (init_options)               │ (during init)      │ during initialize)       │
├──────────────────────────────┼────────────────────┼──────────────────────────┤
│ settings                     │ T5.5 (first time)  │ Yes (can be updated at   │
│ workspace/didChangeConfig    │ T6.2+ (updates)    │ any time after T4)       │
├──────────────────────────────┼────────────────────┼──────────────────────────┤
│ workspace/configuration      │ T5.5+ (on request) │ Yes (pulled dynamically) │
│ (pulled by server)           │                    │                          │
└──────────────────────────────┴────────────────────┴──────────────────────────┘
```

---

## Practical Example: OmniSharp Configuration

```
Neovim init.lua:
═════════════════════════════════════════════════════════════════════════════

omnisharp = {
  -- T0: Spawn server with these args
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio'          ◄─── Command-line argument
  },

  -- T2.5: Sent in initialize request, applied by server
  init_options = {
    -- (typically empty for OmniSharp, but can contain
    --  server-specific startup parameters)
  },

  -- T5.5 onwards: Sent via workspace/didChangeConfiguration,
  --               can be updated dynamically
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,        ◄─── Dynamic setting
      organizeImportsOnFormat = true,      ◄─── Dynamic setting
      enableImportCompletion = true,       ◄─── Dynamic setting
    }
  }
}


Timeline for Typical Session:
═════════════════════════════════════════════════════════════════════════════

:e src/Program.cs
↓
T0: Neovim spawns OmniSharp with: ["omnisharp", "--stdio"]
↓
T1: OmniSharp process starts (running, awaiting init)
↓
T2: Neovim sends initialize with:
    - initializationOptions: {}
    - rootUri: "file:///my/project"
    - capabilities: {...}
↓
T2.5: OmniSharp processes initialize
      (loads initializationOptions - empty in this case)
↓
T3: OmniSharp responds with capabilities
    - definitionProvider: true
    - referencesProvider: true
    - etc.
↓
T4: Neovim sends initialized notification
    (Server is now ready to accept RPC calls)
↓
T5: Neovim sends workspace/didChangeConfiguration with:
    - settings.omnisharp.enableRoslynAnalyzers = true
    - settings.omnisharp.organizeImportsOnFormat = true
↓
T5.5: OmniSharp loads and applies these settings
      (now ready for normal operations)
↓
T6: Editor is functional
    - gd (go to definition) works
    - K (hover) works
    - Code completion works
    - Formatting works
↓
User edits config in init.lua and reloads:
↓
T6.2: Neovim sends new workspace/didChangeConfiguration
      with updated values
↓
T6.5: OmniSharp reloads and applies new settings
      (no server restart needed)
```

---

## Settings Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     THREE PATHS TO CONFIGURATION                             │
└──────────────────────────────────────────────────────────────────────────────┘


PATH 1: Command-Line Arguments (cmd)
═════════════════════════════════════════════════════════════════════════════════

    Neovim init.lua                     Operating System        OmniSharp
    ──────────────────                  ────────────────        ─────────

    cmd = {
      "omnisharp",
      "--stdio"
    }
             │
             ├──────────── spawn process ──────────→ fork process ──→ OmniSharp
             │             with args                                   starts
             │
             │         ◄─── process listening on stdin/stdout ────────┤
             │
    [Cannot change after T0]
    [Controls process behavior only]


PATH 2: Initialization Options (init_options → initializationOptions)
═════════════════════════════════════════════════════════════════════════════════

    Neovim init.lua                     LSP Protocol             OmniSharp
    ──────────────────                  ────────────────         ─────────

    init_options = {
      some_server_option = true
    }
             │
             │
             └──→ JSONified ────→ InitializeParams ──→ T2 Initialize
                                  {                   Request sent
                                    initializationOptions: {
                                      some_server_option: true
                                    }
                                  }
                                                            │
                                                            ├─→ Server reads
                                                            │   initializationOptions
                                                            │   (T2.5)
                                                            │
                                                            ├─→ Applies
                                                            │   settings
                                                            │
                                                            └─→ Responds
                                                                with
                                                                capabilities

    [Cannot change after initialize]
    [Server-specific format]


PATH 3: Settings (settings → workspace/didChangeConfiguration)
═════════════════════════════════════════════════════════════════════════════════

    Neovim init.lua                     LSP Protocol             OmniSharp
    ──────────────────                  ────────────────         ─────────

    settings = {
      omnisharp = {
        enableRoslynAnalyzers = true
      }
    }
             │
             │
             └──→ JSONified ────→ workspace/didChangeConfiguration ──→ T5
                                  Notification                        Notification
                                  {                                   sent
                                    settings: {
                                      omnisharp: {
                                        enableRoslynAnalyzers: true
                                      }
                                    }
                                  }
                                                            │
                                                            ├─→ Server receives
                                                            │   notification
                                                            │   (T5.5)
                                                            │
                                                            ├─→ Applies new
                                                            │   settings
                                                            │
                                                            └─→ Continues
                                                                operation
                                                                (no restart)

    [CAN change dynamically]
    [Can be updated without restart]
    [Server-specific format for keys]


(Optional) PATH 3B: Dynamic Configuration Pulling
═════════════════════════════════════════════════════════════════════════════════

    OmniSharp                           LSP Protocol             Neovim
    ─────────                           ────────────────         ──────

    Needs setting                       workspace/configuration
    for "omnisharp"                     Request
    section                             │
         │                              │
         └──── workspace/configuration ─────→ Receives request
               Request sent             │    with section: "omnisharp"
               (T5+)                    │
                                        ├──→ Looks up settings
                                        │    from Neovim config
                                        │
                                        ├──→ Returns workspace/
                                        │    configuration Response
                                        │
               ←──── Response ──────────┤
               with matching            │
               settings                 │
                     │
                     ├──→ Server updates
                          its cached
                          settings
```

---

## Decision Tree: Which Setting Path to Use?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  WHEN TO USE WHICH SETTING MECHANISM                         │
└─────────────────────────────────────────────────────────────────────────────┘

START: How does your server need this configuration?
  │
  ├─── Do you need to control HOW THE PROCESS IS STARTED? (e.g., with flags)
  │    │
  │    └─→ YES
  │        │
  │        └──→ Use: cmd (command-line arguments)
  │            └─→ Example: cmd = { "omnisharp", "--stdio", "--port=8080" }
  │            └─→ Timing: T0 (process spawn)
  │            └─→ Changeable: NO
  │
  ├─── Is this a STATIC, SERVER-SPECIFIC startup parameter that shouldn't change?
  │    │
  │    └─→ YES
  │        │
  │        └──→ Use: init_options (initializationOptions)
  │            └─→ Example: { defaultLanguageVersion: "latest" }
  │            └─→ Timing: T2 (during initialize)
  │            └─→ Changeable: NO
  │
  └─── Do you need DYNAMIC configuration that can change WITHOUT restart?
       │
       └─→ YES
           │
           └──→ Use: settings (workspace/didChangeConfiguration)
               └─→ Example: { omnisharp: { enableRoslynAnalyzers: true } }
               └─→ Timing: T5+ (after initialized)
               └─→ Changeable: YES


IMPLEMENTATION DECISION:

Does the server documentation mention the configuration option?
│
├─→ Only in "startup options" or "command line" section?
│   Use: cmd
│
├─→ Only in "initialization" or "initialize request" section?
│   Use: init_options
│
├─→ In "workspace configuration" or "settings" section?
│   Use: settings
│
├─→ Doesn't specify where?
│   Try: settings (most common, most flexible)
│   If that doesn't work: Try init_options
│   If that doesn't work: Check if it's a cmd arg
│
└─→ Works with environment variables?
    Can use: environment variables before starting Neovim
    (export VAR=value before nvim)
```

---

## Summary Table

```
┌──────────────────┬──────────────────┬──────────────┬─────────────────┐
│ Setting Type     │ Lua Config Field │ Timing       │ Changeable      │
├──────────────────┼──────────────────┼──────────────┼─────────────────┤
│ Process Args     │ cmd              │ T0 (spawn)   │ No              │
│ Initialization   │ init_options     │ T2 (init)    │ No              │
│ Dynamic Config   │ settings         │ T5+ (ready)  │ Yes             │
│ Pulled Config    │ (pulled by svr)  │ T5+ (on req) │ Yes (dynamic)   │
│ Config Files     │ (external)       │ Svr-depends  │ Svr-depends     │
│ Environment      │ (external)       │ Before start │ No              │
└──────────────────┴──────────────────┴──────────────┴─────────────────┘
```

---

## References

- LSP Specification 3.17: Initialize Request and workspace/didChangeConfiguration
- Neovim LSP Documentation: :help lsp-configuration
- OmniSharp Documentation: https://github.com/OmniSharp/omnisharp-roslyn

