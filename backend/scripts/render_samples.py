"""Turn every samples/*.html into two images: a clean scan and a fake phone photo.

    python scripts/render_samples.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

SAMPLES = Path(__file__).parent.parent / "samples"

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

with sync_playwright() as p:
    browser = p.chromium.launch()
    for html in sorted(SAMPLES.glob("*.html")):
        # Clean version: sharp, cropped to the page, like a scanner or a PDF export.
        page = browser.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=2)
        page.goto(html.as_uri())
        page.locator("body").screenshot(path=html.with_suffix(".png"))
        page.close()

        # Photo version: lower resolution, tilted, blurred, heavily compressed JPEG.
        page = browser.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=1)
        page.goto(html.as_uri())
        page.add_style_tag(content=PHOTO_CSS)
        page.screenshot(path=SAMPLES / f"{html.stem}.photo.jpg", full_page=True, type="jpeg", quality=40)
        page.close()

        print("rendered", html.name)
    browser.close()
