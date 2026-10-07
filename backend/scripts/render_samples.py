"""Turn every HTML document in a folder into three images: a clean scan, a phone photo and a rough phone photo.

    python -m scripts.render_samples            # the hand-made documents in samples/
    python -m scripts.render_samples dataset    # the generated test set
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

FOLDER = Path(__file__).parent.parent / (sys.argv[1] if len(sys.argv) > 1 else "samples")

# Added on top of the page for the "photo" version:
# paper lying on a desk, slightly tilted, a little out of focus, darker on one side.
PHOTO_CSS = """
html { background: #5b5148; }
body {
  margin: 70px auto !important;
  transform: perspective(1600px) rotateX(4deg) rotateZ(-2.5deg);
  filter: blur(0.7px) contrast(0.88) brightness(0.95);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.55);
  background-image: linear-gradient(115deg, rgba(0, 0, 0, 0) 40%, rgba(0, 0, 0, 0.18) 100%) !important;
}
"""

# The "rough" version: a hurried photo in bad light, at an angle, with a shadow across the page.
ROUGH_CSS = """
html { background: #3a332d; }
body {
  margin: 90px auto !important;
  transform: perspective(1100px) rotateX(9deg) rotateY(-6deg) rotateZ(4deg);
  filter: blur(1.1px) contrast(0.78) brightness(0.84) saturate(0.8);
  box-shadow: 0 22px 50px rgba(0, 0, 0, 0.7);
  background-image: linear-gradient(100deg, rgba(0, 0, 0, 0) 30%, rgba(0, 0, 0, 0.3) 58%, rgba(0, 0, 0, 0.05) 80%) !important;
}
"""

# name suffix, extra CSS, pixels per CSS pixel, JPEG quality (None = PNG cropped to the page)
VERSIONS = [
    (".png", None, 2, None),
    (".photo.jpg", PHOTO_CSS, 1, 40),
    (".rough.jpg", ROUGH_CSS, 0.8, 22),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    pages = sorted(FOLDER.glob("*.html"))
    for html in pages:
        for suffix, css, scale, quality in VERSIONS:
            page = browser.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=scale)
            page.goto(html.as_uri())
            target = FOLDER / f"{html.stem}{suffix}"
            if css is None:
                page.locator("body").screenshot(path=target)
            else:
                page.add_style_tag(content=css)
                page.screenshot(path=target, full_page=True, type="jpeg", quality=quality)
            page.close()
    browser.close()
    print(f"rendered {len(pages)} documents x {len(VERSIONS)} versions in {FOLDER.name}/")
