import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
INPUT_FILE = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/organized_texts.txt"
OUTPUT_PDF = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/04_extracted_info/labels.pdf"

LABEL_WIDTH_MM = 53.0   # label width (mm)
LABEL_HEIGHT_MM = 20.0  # label height (mm)

# Convert mm to points
LABEL_WIDTH = LABEL_WIDTH_MM * mm
LABEL_HEIGHT = LABEL_HEIGHT_MM * mm

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 10 * mm

# Reserve space at the top for the header that shows total locations
HEADER_SPACE = 20  # in points

# Calculate how many columns/rows fit on one page (using the grid below the header)
cols_per_page = int((PAGE_WIDTH - 2 * MARGIN) // LABEL_WIDTH)
rows_per_page = int((PAGE_HEIGHT - 2 * MARGIN - HEADER_SPACE) // LABEL_HEIGHT)

# Fonts
LOCATION_FONT = ("Helvetica-Bold", 14)  # large for Location
MPN_FONT_NAME = "Helvetica"             # base font name for MFG/PN
MPN_FONT_SIZE = 10                      # initial size for MFG/PN
DESC_FONT = ("Helvetica", 8)            # smaller for Description

DESC_LINE_SPACING = 9
TRUNCATE_ELLIPSIS = "..."

# Minimum font size for MFG/PN before truncation
MIN_MPN_FONT_SIZE = 6

# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------


def parse_location(loc):
    """
    Parses a location string like 'C10' into (prefix, number) = ('C', 10).
    If no match, returns (loc, 999999) so that unparsed strings go last.
    This allows us to sort in a natural 'alphabet + numeric' manner.
    """
    match = re.match(r"^([A-Za-z]+)(\d+)$", loc.strip())
    if match:
        prefix = match.group(1).upper()
        number = int(match.group(2))
        return (prefix, number)
    else:
        # fallback if the location doesn't match <letters><digits>
        return (loc.strip().upper(), 999999)


def single_line_centered_truncate(c, text, x, y, box_width, font_name, font_size):
    """
    Draw 'text' in one line, centered within box_width at (x, y).
    If it doesn't fit horizontally, truncate with "...".
    """
    c.setFont(font_name, font_size)
    text_width = c.stringWidth(text, font_name, font_size)
    max_width = box_width - 4  # small side margin

    if text_width <= max_width:
        # Fits without truncation
        text_x = x + (box_width - text_width) / 2
        c.drawString(text_x, y, text)
    else:
        # Need to truncate
        ell = TRUNCATE_ELLIPSIS
        while text and c.stringWidth(text + ell, font_name, font_size) > max_width:
            text = text[:-1]
        text += ell
        new_width = c.stringWidth(text, font_name, font_size)
        text_x = x + (box_width - new_width) / 2
        c.drawString(text_x, y, text)


def single_line_centered_fit(c, text, x, y, box_width,
                             font_name, initial_font_size, min_font_size=6):
    """
    Draw 'text' in one line, centered, ensuring it fits horizontally.
    - Start from 'initial_font_size' and keep reducing by 1 until it fits
      or 'min_font_size'.
    - If it still doesn't fit at min_font_size, truncate with "...".
    """
    size = initial_font_size
    max_width = box_width - 4  # small margin
    while size >= min_font_size:
        text_width = c.stringWidth(text, font_name, size)
        if text_width <= max_width:
            # It fits at this size
            c.setFont(font_name, size)
            text_x = x + (box_width - text_width) / 2
            c.drawString(text_x, y, text)
            return
        size -= 1

    # Must truncate at min_font_size
    c.setFont(font_name, min_font_size)
    ell = TRUNCATE_ELLIPSIS
    while text and c.stringWidth(text + ell, font_name, min_font_size) > max_width:
        text = text[:-1]
    text += ell
    new_width = c.stringWidth(text, font_name, min_font_size)
    text_x = x + (box_width - new_width) / 2
    c.drawString(text_x, y, text)


def wrap_text(text, font_name, font_size, max_width):
    """
    Split 'text' into multiple lines so that no line exceeds 'max_width' in points.
    Returns a list of lines (strings).
    """
    words = text.split()
    lines = []
    current_line = []

    for w in words:
        test_line = current_line + [w] if current_line else [w]
        line_str = " ".join(test_line)
        width = stringWidth(line_str, font_name, font_size)
        if width <= max_width:
            current_line.append(w)
        else:
            lines.append(" ".join(current_line))
            current_line = [w]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def draw_wrapped_centered(c, text, x, y, box_width, box_height, font_name, font_size, line_spacing):
    """
    Draw 'text' center-aligned, wrapped within (x, y, box_width, box_height).
    If it doesn't fit vertically, truncate with "...".
    Returns the final y position after drawing.
    """
    c.setFont(font_name, font_size)
    lines = wrap_text(text, font_name, font_size, box_width - 4)
    draw_y = y + box_height - font_size - 2  # start near top

    for i, line in enumerate(lines):
        if draw_y < y + 4:  # no space left
            # Truncate with ...
            if i > 0:
                c.drawString(
                    x + (box_width - stringWidth(TRUNCATE_ELLIPSIS,
                         font_name, font_size)) / 2,
                    draw_y + line_spacing,
                    TRUNCATE_ELLIPSIS
                )
            return draw_y
        line_width = stringWidth(line, font_name, font_size)
        line_x = x + (box_width - line_width) / 2
        c.drawString(line_x, draw_y, line)
        draw_y -= line_spacing

    return draw_y


# -------------------------------------------------------------------------
# STEP 1: READ AND PARSE INPUT
# -------------------------------------------------------------------------
with open(INPUT_FILE, "r") as f:
    content = f.read().strip()

# Each entry is separated by two newlines
entries = [e.strip() for e in content.split("\n\n") if e.strip()]

labels = []
for entry in entries:
    loc_match = re.search(r"^Location:\s*(.+)$", entry, re.MULTILINE)
    desc_match = re.search(r"^Description:\s*(.+)$", entry, re.MULTILINE)
    mfgpn_match = re.search(
        r"^Manufacturer Part number:\s*(.+)$", entry, re.MULTILINE)

    location = loc_match.group(1).strip() if loc_match else ""
    description = desc_match.group(1).strip() if desc_match else ""
    mfgpn = mfgpn_match.group(1).strip() if mfgpn_match else ""

    # Add "MFG/PN: " prefix
    if mfgpn:
        mfgpn = f"MFG/PN: {mfgpn}"

    labels.append((location, mfgpn, description))

# -------------------------------------------------------------------------
# STEP 2: SORT THE LABELS
# -------------------------------------------------------------------------
# Sort by parsed location: e.g., "C1" < "C2" < "C10" < "R1" < "R2" < ...
labels.sort(key=lambda x: parse_location(x[0]))

# -------------------------------------------------------------------------
# STEP 3: CREATE THE PDF AND LAY OUT THE LABELS
# -------------------------------------------------------------------------
c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)

# Draw header on the first page with the total locations assigned
total_locations = len(labels)
header_text = f"Total locations assigned: {total_locations}"
c.setFont("Helvetica", 12)
c.drawString(MARGIN, PAGE_HEIGHT - MARGIN - HEADER_SPACE/2, header_text)

# Adjust starting point for the label grid (below the header)
x_start = MARGIN
y_start = PAGE_HEIGHT - MARGIN - HEADER_SPACE - LABEL_HEIGHT

col = 0
row = 0

for (location, mfgpn, description) in labels:
    # Compute label's lower-left corner
    x = x_start + col * LABEL_WIDTH
    y = y_start - row * LABEL_HEIGHT

    # Draw the label outline (optional)
    c.rect(x, y, LABEL_WIDTH, LABEL_HEIGHT)

    # 1) LOCATION at top (centered, single line, truncated if needed)
    loc_y = y + LABEL_HEIGHT - (LOCATION_FONT[1] + 2)
    single_line_centered_truncate(
        c, location, x, loc_y, LABEL_WIDTH, LOCATION_FONT[0], LOCATION_FONT[1]
    )

    # 2) MFG/PN: shrink font if needed, then truncate if still too wide
    mpn_y = loc_y - (MPN_FONT_SIZE + 4)
    single_line_centered_fit(
        c, mfgpn, x, mpn_y, LABEL_WIDTH,
        MPN_FONT_NAME, MPN_FONT_SIZE, min_font_size=MIN_MPN_FONT_SIZE
    )

    # 3) DESCRIPTION (centered, wrapped) below MFG/PN
    desc_top_space = mpn_y - (DESC_FONT[1] + 2) - y
    if desc_top_space > 0:
        draw_wrapped_centered(
            c,
            description,
            x,
            y,
            LABEL_WIDTH,
            desc_top_space,
            DESC_FONT[0],
            DESC_FONT[1],
            DESC_LINE_SPACING
        )

    # Move to the next label position
    row += 1
    if row >= rows_per_page:
        row = 0
        col += 1
        if col >= cols_per_page:
            # Start a new page; note that header is added only on the first page.
            c.showPage()
            col = 0
            row = 0
            # If you want the header on subsequent pages, repeat the header drawing here.
            x_start = MARGIN
            y_start = PAGE_HEIGHT - MARGIN - HEADER_SPACE - LABEL_HEIGHT

c.save()
print(f"Labels PDF saved as {OUTPUT_PDF}")
