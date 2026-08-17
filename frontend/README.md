# NoRefund frontend

## Develop (hot reload)

Two terminals:

    cd frontend && npm run dev          # Vite on :5173
    NOREFUND_DEV=1 python -m norefund.desktop.app

The window loads from the dev server, so React edits hot-reload in place.
`NOREFUND_DEV=1` also enables the webview devtools (right-click → Inspect).

## Build (what ships)

    cd frontend && npm run build        # emits ../src/norefund/web/
    python -m norefund.desktop.app

## Rules

- No remote assets. The CSP in `index.html` blocks them.
- No new dependency without a line in the relevant `GUI_REBUILD/` phase file.
