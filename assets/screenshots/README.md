# Screenshots

Drop PNG screenshots in this directory using the filenames referenced
in the project README. Keep each image **under 500 KB** (compress with
`pngquant`, `oxipng`, or `tinypng.com` if needed). Prefer 1280–1600 px
wide; the README will scale them down for display.

## Required files

| Filename | What to capture |
|---|---|
| `kanban.png` | The main Kanban board with at least 3 tasks in different lanes (Backlog / In Progress / Done). Avoid any personal data — use a dummy/throwaway project. |
| `task-wizard.png` | The "New Task" creation wizard, ideally showing the complexity / track selection step. |
| `terminal.png` | The browser-embedded PTY terminal running `ls` or `git status` inside a project. |
| `editor.png` | The Monaco code editor open on a representative file (e.g. a Python or TSX file). |
| `settings.png` | The Settings page — provider selection or general settings. |

## Capture tips

- Use a clean browser profile (no extension toolbars, no personal bookmarks bar).
- System dark mode is fine; keep it consistent across all images.
- Sanitise visible paths and project names before exporting — nothing
  user-identifying should leak through.
- On Linux: `gnome-screenshot -w -d 3` (window, 3 s delay) or the
  Screenshot Tool / Flameshot.

## After adding

1. Verify each image displays in the README preview (`gh pr view --web`
   or any markdown viewer).
2. `git add assets/screenshots/*.png && git commit`.
