# Nursery MCP Server

Three tools for the Stage 1 "nursery" agent. It calls a tool for every
question and repeats the returned value verbatim. The combo challenge just
means the agent will chain calls to these same three tools in sequence, so
no fourth tool was needed.

## Tools

| Tool | Input | Output |
|---|---|---|
| `what_is_my_name` | none | name string (3–30 chars, matches the allowed charset) |
| `do_arithmetic` | `operator` (`+ - * /`), `a`, `b` (ints, -100..100) | number |
| `identify_shape` | `image_base64` (base64 PNG) | `"rectangle"` \| `"triangle"` \| `"circle"` |

`identify_shape` uses OpenCV contour analysis: it thresholds the image
(trying both polarities, since the shape can be dark-on-light or
light-on-dark), discards any contour that just traces the image's own
border, then classifies by polygon-approximation vertex count (3 = triangle,
4 = rectangle) or circularity (>0.8 = circle). Verified against the provided
example image (correctly returns `rectangle`) and a battery of synthetic
filled/outline shapes on both backgrounds, including non-square rectangles
and rotated squares.

## Run locally

```bash
pip install -r requirements.txt
python3 server.py
```

Serves Streamable HTTP MCP at `http://0.0.0.0:8000/mcp`. Confirmed working
end-to-end: `initialize`, `tools/list`, and `tools/call` all tested live
against a running instance, including error handling for out-of-range
operands and division by zero.

## Exposing it at `{teamUrl}/mcp`

This server binds locally to port 8000 at path `/mcp`. To make it reachable
at your team's public `{teamUrl}/mcp`, point a reverse proxy or tunnel at
`localhost:8000` — e.g. deploy to Render/Fly.io/Railway with the exposed
port set to 8000, or run behind nginx with:

```
location /mcp {
    proxy_pass http://127.0.0.1:8000/mcp;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

I can't host a publicly reachable URL myself from this environment — you'll
need to deploy this file to wherever `{teamUrl}` resolves (a VPS, container
platform, or tunnel like ngrok/Cloudflare Tunnel pointed at port 8000).
