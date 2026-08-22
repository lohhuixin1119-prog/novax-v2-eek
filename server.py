"""
Nursery MCP Server
-------------------
Exposes three tools for the "Stage 1" agent, which knows nothing on its own
and must ask a tool for every answer, then repeat that answer verbatim.

Tools:
  1. what_is_my_name   -> returns a valid name string
  2. do_arithmetic     -> evaluates +, -, *, / on two integers in [-100, 100]
  3. identify_shape    -> classifies a base64-encoded PNG as
                          "rectangle", "triangle", or "circle"

Run:
    python3 server.py
This starts a Streamable HTTP MCP server on 0.0.0.0:8000, mounted at /mcp
(so a reverse proxy / tunnel serving this at {teamUrl}/mcp works out of the box).
"""

import base64
import io

import cv2
import numpy as np
from mcp.server import MCPServer

mcp = MCPServer("nursery-mcp")

# ---------------------------------------------------------------------------
# Tool 1: Name
# ---------------------------------------------------------------------------

# Any string 3-30 chars, using only letters/digits/spaces/_/-/' satisfies the
# grader. Hardcode a friendly, valid name for the agent to give back verbatim.
NURSERY_NAME = "Sonnet Junior"


@mcp.tool(
    name="what_is_my_name",
    description=(
        "Returns the agent's own name. Call this whenever asked 'What is your "
        "name?' or similar, and reply with the returned string exactly."
    ),
)
def what_is_my_name() -> str:
    return NURSERY_NAME


# ---------------------------------------------------------------------------
# Tool 2: Arithmetic
# ---------------------------------------------------------------------------

_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}


@mcp.tool(
    name="do_arithmetic",
    description=(
        "Computes the result of a basic arithmetic expression 'a <operator> b'. "
        "operator must be one of '+', '-', '*', '/'. a and b must be integers "
        "in the range -100 to 100. Call this whenever asked a math question "
        "like 'What is 2 + 2?', and reply with the returned number."
    ),
)
def do_arithmetic(operator: str, a: int, b: int) -> float:
    if operator not in _OPS:
        raise ValueError(f"Unsupported operator: {operator!r}. Must be one of +, -, *, /.")
    for name, val in (("a", a), ("b", b)):
        if not (-100 <= val <= 100):
            raise ValueError(f"{name}={val} is out of the allowed range [-100, 100].")
    if operator == "/" and b == 0:
        raise ValueError("Division by zero is not allowed.")

    result = _OPS[operator](a, b)
    # Return an int when the result is a whole number, otherwise a float.
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return result


# ---------------------------------------------------------------------------
# Tool 3: Shape identification
# ---------------------------------------------------------------------------


def _classify_shape(image_base64: str) -> str:
    raw = base64.b64decode(image_base64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not decode image; expected a base64-encoded PNG.")

    _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    img_area = img.shape[0] * img.shape[1]

    # Shapes may be drawn dark-on-light or light-on-dark. Try both polarities
    # and discard any contour that just traces the outer image frame (i.e. the
    # background got picked up as "foreground").
    contours = []
    for candidate in (thresh, cv2.bitwise_not(thresh)):
        found, _ = cv2.findContours(candidate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        found = [c for c in found if 50 < cv2.contourArea(c) < 0.95 * img_area]
        if found:
            contours = found
            break

    if not contours:
        raise ValueError("No shape could be found in the image.")

    c = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.03 * peri, True)
    vertices = len(approx)

    area = cv2.contourArea(c)
    circularity = 4 * np.pi * area / (peri * peri) if peri > 0 else 0

    if vertices == 3:
        return "triangle"
    elif vertices == 4:
        return "rectangle"
    elif circularity > 0.8:
        return "circle"
    elif vertices >= 8:
        return "circle"
    else:
        return "rectangle"


@mcp.tool(
    name="identify_shape",
    description=(
        "Identifies the shape drawn in a base64-encoded PNG image. Returns "
        "exactly one of: 'rectangle', 'triangle', 'circle'. Call this "
        "whenever asked 'What shape is this?' along with an image, and reply "
        "with the returned word exactly."
    ),
)
def identify_shape(image_base64: str) -> str:
    return _classify_shape(image_base64)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Streamable HTTP transport serves at http://<host>:<port>/mcp by default,
    # so {teamUrl}/mcp works when this is reverse-proxied / tunneled.
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        stateless_http=True,
    )
