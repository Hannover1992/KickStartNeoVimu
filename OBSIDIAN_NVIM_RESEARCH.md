# Obsidian.nvim Research Report

**Datum**: 2025-01-16
**Status**: Phase 1 - Forschung abgeschlossen
**Ziel**: Vollständige Obsidian-Integration in Neovim mit Image-Support

---

## Executive Summary

Die aktuelle Obsidian-Konfiguration in `init.lua` ist **minimal** und fehlt wichtige Einstellungen. Das erklärt warum:
- `:Obsidian today` funktioniert
- `:Obsidian new` Notizen "verliert" (erstellt sie im falschen Ordner)

---

## 1. Architektur-Übersicht

### Obsidian Ecosystem

```mermaid
flowchart TB
    subgraph Mobile["Handy (Android/iOS)"]
        OA[Obsidian App]
        CAM[Kamera]
        CAM -->|Foto aufnehmen| OA
    end

    subgraph Cloud["Obsidian Sync"]
        SYNC[(Cloud Storage)]
    end

    subgraph PC["Windows PC"]
        OD[Obsidian Desktop]
        NV[Neovim + obsidian.nvim]
        VAULT[(Vault Ordner)]

        OD <-->|liest/schreibt| VAULT
        NV <-->|liest/schreibt| VAULT
    end

    OA <-->|synchronisiert| SYNC
    SYNC <-->|synchronisiert| VAULT

    style NV fill:#98c379,stroke:#333
    style SYNC fill:#61afef,stroke:#333
```

### Dateistruktur eines Obsidian Vaults

```mermaid
flowchart LR
    subgraph Vault["Brain/ (Vault Root)"]
        direction TB
        subgraph Notes["Notes/"]
            N1[note1.md]
            N2[note2.md]
        end
        subgraph Daily["Daily/"]
            D1[2025-01-16.md]
            D2[2025-01-15.md]
        end
        subgraph Attach["attachments/"]
            I1[Pasted image 123.png]
            I2[foto-vom-handy.jpg]
        end
        subgraph Templates["templates/"]
            T1[daily.md]
            T2[meeting.md]
        end
    end
```

---

## 2. Problem-Analyse

### Warum "Neue Notizen funktionieren nicht"

```mermaid
flowchart TD
    subgraph Problem["Das Problem"]
        USER[User drückt leader+on]
        CMD[":Obsidian new"]
        CHECK{Wo ist der Cursor?}

        USER --> CMD --> CHECK

        CHECK -->|In Vault| OK[Notiz wird erstellt in CURRENT_DIR]
        CHECK -->|Außerhalb Vault| FAIL[FEHLER: Kein Workspace gefunden]

        OK --> WHERE{Wo landet die Notiz?}
        WHERE -->|current_dir default| WRONG[Im aktuellen Ordner - FALSCH!]
        WHERE -->|notes_subdir| RIGHT[Im konfigurierten Ordner - RICHTIG!]
    end

    style FAIL fill:#e06c75,stroke:#333
    style WRONG fill:#e5c07b,stroke:#333
    style RIGHT fill:#98c379,stroke:#333
```

### Aktuelle Config vs. Empfohlene Config

| Setting | Aktuell | Default | Empfohlen | Auswirkung |
|---------|---------|---------|-----------|------------|
| `notes_subdir` | - | `nil` | `"Notes"` | Wo neue Notizen landen |
| `new_notes_location` | - | `"current_dir"` | `"notes_subdir"` | Relativ zu was? |
| `daily_notes.folder` | - | `nil` | `"Daily"` | Wo Daily Notes landen |
| `daily_notes.date_format` | - | `"%Y-%m-%d"` | `"%Y-%m-%d"` | Dateiname-Format |
| `templates.folder` | - | `nil` | `"templates"` | Template-Ordner |
| `attachments.folder` | - | `"attachments"` | `"attachments"` | Wo Bilder landen |

### Warum `:Obsidian today` funktioniert

```mermaid
flowchart LR
    TODAY[":Obsidian today"] --> DAILY["daily_notes.folder"]
    DAILY --> ROOT["Vault Root (default)"]
    ROOT --> FILE["2025-01-16.md"]
    FILE --> SUCCESS["Funktioniert!"]

    style SUCCESS fill:#98c379
```

### Warum `:Obsidian new` fehlschlägt

```mermaid
flowchart LR
    NEW[":Obsidian new"] --> LOC["new_notes_location"]
    LOC --> CURR["current_dir (default)"]
    CURR --> CHECK{Bist du im Vault?}
    CHECK -->|Ja| RANDOM["Notiz im aktuellen Ordner"]
    CHECK -->|Nein| ERROR["Fehler!"]

    style ERROR fill:#e06c75
    style RANDOM fill:#e5c07b
```

---

## 3. Image-Handling Deep Dive

### Wie Bilder in Obsidian funktionieren

```mermaid
flowchart TB
    subgraph Input["Bild-Quellen"]
        MOBILE[Handy-Foto via Obsidian App]
        PASTE[Clipboard Paste in Desktop]
        DRAG[Drag & Drop]
    end

    subgraph Storage["Speicherung"]
        ATTACH["attachments/ Ordner"]
        SYNC2[(Obsidian Sync)]
    end

    subgraph Reference["Referenz in Markdown"]
        WIKI["![[bild.png]]<br/>(Wiki-Style)"]
        MD["![alt](attachments/bild.png)<br/>(Markdown-Style)"]
    end

    subgraph Viewing["Anzeige in Neovim"]
        SNACKS["snacks.image<br/>(Float Window)"]
        UIOPEN["vim.ui.open<br/>(System Viewer)"]
        KITTY["Kitty Graphics Protocol<br/>(Inline - nur Linux/Mac)"]
    end

    MOBILE --> SYNC2 --> ATTACH
    PASTE --> ATTACH
    DRAG --> ATTACH

    ATTACH --> WIKI
    ATTACH --> MD

    WIKI --> SNACKS
    WIKI --> UIOPEN
    MD --> SNACKS
    MD --> UIOPEN

    style SNACKS fill:#61afef
    style UIOPEN fill:#98c379
    style KITTY fill:#e5c07b
```

### Windows Limitierungen

```mermaid
flowchart TD
    subgraph Windows["Windows Terminal Support"]
        WT[Windows Terminal]
        WEZTERM[Wezterm]
        PWSH[PowerShell/CMD]
    end

    subgraph Features["Image Features"]
        INLINE["Inline Images<br/>(im Buffer)"]
        FLOAT["Float Images<br/>(schwebendes Fenster)"]
        EXTERNAL["External Viewer<br/>(Windows Fotos)"]
    end

    WT -->|Nicht unterstützt| INLINE
    WEZTERM -->|Nightly + begrenzt| FLOAT
    PWSH -->|Nicht unterstützt| INLINE

    WT -->|Nicht unterstützt| FLOAT
    WEZTERM -->|Funktioniert| FLOAT

    WT -->|Funktioniert| EXTERNAL
    WEZTERM -->|Funktioniert| EXTERNAL
    PWSH -->|Funktioniert| EXTERNAL

    style INLINE fill:#e06c75
    style FLOAT fill:#e5c07b
    style EXTERNAL fill:#98c379
```

### Empfehlung für Windows

| Option | Terminal | Komplexität | Ergebnis |
|--------|----------|-------------|----------|
| `vim.ui.open` | Alle | Einfach | Öffnet Windows Foto-Viewer |
| `snacks.image` Float | Wezterm Nightly | Mittel | Schwebendes Fenster in Neovim |
| Inline Images | Nicht möglich | - | Windows unterstützt Kitty Protocol nicht |

---

## 4. Plugin-Abhängigkeiten

### Aktuell installiert

```mermaid
flowchart LR
    subgraph Installed["Bereits in init.lua"]
        OBS["obsidian-nvim/obsidian.nvim"]
        PLENARY["nvim-lua/plenary.nvim"]
    end

    OBS -->|dependency| PLENARY

    style OBS fill:#98c379
    style PLENARY fill:#98c379
```

### Empfohlene Erweiterungen

```mermaid
flowchart TB
    subgraph Core["Core (bereits installiert)"]
        OBS["obsidian.nvim"]
    end

    subgraph Optional["Optional - Image Viewing"]
        SNACKS["folke/snacks.nvim"]
        MAGICK["ImageMagick (System)"]
    end

    subgraph Completion["Optional - Completion"]
        BLINK["blink.cmp"]
        CMP["nvim-cmp"]
    end

    OBS -.->|für Images| SNACKS
    SNACKS -->|benötigt| MAGICK

    OBS -.->|für [[links]]| BLINK
    OBS -.->|alternativ| CMP

    style OBS fill:#98c379
    style SNACKS fill:#61afef
    style BLINK fill:#c678dd
```

---

## 5. Lösungsvorschlag

### Schritt 1: Erweiterte Obsidian Config

```lua
-- Vorgeschlagene Konfiguration
opts = {
  legacy_commands = false,

  workspaces = {
    { name = 'DCSRE', path = '...' },
    { name = 'CenCoCo', path = '...' },
    { name = 'Brain', path = '...' },
  },

  -- NEU: Wo neue Notizen landen
  notes_subdir = 'Notes',
  new_notes_location = 'notes_subdir',

  -- NEU: Daily Notes Konfiguration
  daily_notes = {
    folder = 'Daily',
    date_format = '%Y-%m-%d',
    default_tags = { 'daily' },
  },

  -- NEU: Templates
  templates = {
    folder = 'templates',
    date_format = '%Y-%m-%d',
    time_format = '%H:%M',
  },

  -- NEU: Attachments (Bilder)
  attachments = {
    folder = 'attachments',
    confirm_img_paste = true,
  },

  -- NEU: Wie Bilder geöffnet werden (Enter auf Bild-Link)
  follow_img_func = function(url)
    vim.ui.open(url)  -- Öffnet im Windows Foto-Viewer
  end,
}
```

### Schritt 2: Neue Keybindings

```lua
keys = {
  -- Bestehende...
  { '<leader>on', '<cmd>Obsidian new<cr>', desc = '[O]bsidian [N]ew note' },
  { '<leader>ot', '<cmd>Obsidian today<cr>', desc = '[O]bsidian [T]oday' },

  -- NEU: Template-basierte Notiz
  { '<leader>oT', '<cmd>Obsidian new_from_template<cr>', desc = '[O]bsidian [T]emplate' },

  -- NEU: Bild einfügen
  { '<leader>oi', '<cmd>Obsidian paste_img<cr>', desc = '[O]bsidian [I]mage paste' },

  -- NEU: Link folgen (auch für Bilder)
  { '<leader>of', '<cmd>Obsidian follow_link<cr>', desc = '[O]bsidian [F]ollow link' },

  -- NEU: Tägliche Notizen Browser
  { '<leader>od', '<cmd>Obsidian dailies<cr>', desc = '[O]bsidian [D]ailies list' },
}
```

### Schritt 3 (Optional): snacks.nvim für Float-Images

```lua
-- Nur wenn du Wezterm Nightly verwendest
{
  'folke/snacks.nvim',
  opts = {
    image = {
      enabled = true,
      -- Integration mit obsidian.nvim
      resolve = function(path, src)
        local ok, api = pcall(require, 'obsidian.api')
        if ok and api.path_is_note(path) then
          return api.resolve_attachment_path(src)
        end
      end,
    },
  },
}
```

---

## 6. Workflow nach Implementation

### Neue Notiz erstellen

```mermaid
flowchart LR
    A["leader+on"] --> B["Titel eingeben"]
    B --> C["Notiz erstellt in<br/>Vault/Notes/titel.md"]
    C --> D["Cursor in neuer Datei"]

    style C fill:#98c379
```

### Bild einfügen

```mermaid
flowchart LR
    A["Screenshot in Clipboard"] --> B["leader+oi"]
    B --> C["Bild gespeichert in<br/>attachments/Pasted image....png"]
    C --> D["Link eingefügt:<br/>![[Pasted image....png]]"]

    style C fill:#98c379
    style D fill:#98c379
```

### Bild anzeigen (Enter auf Link)

```mermaid
flowchart LR
    A["Cursor auf ![[bild.png]]"] --> B["Enter / gf"]
    B --> C{follow_img_func}
    C -->|vim.ui.open| D["Windows Foto-Viewer öffnet"]
    C -->|snacks.image| E["Float-Fenster in Neovim"]

    style D fill:#98c379
    style E fill:#61afef
```

---

## 7. Offene Fragen

1. **Welche Ordnerstruktur** verwendest du in deinen Vaults?
   - Hast du bereits `Notes/`, `Daily/`, `attachments/` Ordner?
   - Oder eine andere Struktur?

2. **Welches Terminal** verwendest du?
   - Windows Terminal → nur `vim.ui.open` möglich
   - Wezterm → Float-Images möglich (mit Nightly + ImageMagick)

3. **Obsidian Sync** - Welche Vaults werden synchronisiert?
   - Brain?
   - CenCoCo?
   - DCSRE?

---

## 8. Nächste Schritte

| Phase | Aktion | Status |
|-------|--------|--------|
| 1 | Forschung abschließen | ✅ Erledigt |
| 2 | User-Feedback zu Ordnerstruktur | ⏳ Warte auf Antwort |
| 3 | Config implementieren | ⏳ Pending |
| 4 | Testen | ⏳ Pending |
| 5 | Dokumentation aktualisieren | ⏳ Pending |

---

## Quellen

- [obsidian-nvim/obsidian.nvim (GitHub)](https://github.com/obsidian-nvim/obsidian.nvim)
- [Images Wiki](https://github.com/obsidian-nvim/obsidian.nvim/wiki/Images)
- [Commands Wiki](https://github.com/obsidian-nvim/obsidian.nvim/wiki/Commands)
- [snacks.nvim Image Viewer](https://github.com/folke/snacks.nvim/blob/main/docs/image.md)
- [snacks.image Windows Compatibility](https://github.com/folke/snacks.nvim/discussions/1720)
- [linkarzu - Obsidian to Neovim](https://linkarzu.com/posts/neovim/obsidian-to-neovim/)
