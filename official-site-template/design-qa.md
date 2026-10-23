# Design QA — Textoria Markup product website

final result: passed

## Evidence and state

- Source visual truth: `qa/reference.png`, the third displayed design selected by the user.
- Implementation URL: `http://127.0.0.1:4173/`.
- Source pixels: 946 × 1663. Final implementation: `qa/desktop-final.png`, 946 × 1663.
- CSS viewport: 946 × 1663, devicePixelRatio 1; no density normalization or stretching. Explicit screenshot clip used because default screenshot capture capped height at 1200.
- State: top of page, install dialog closed, main navigation closed, default content; final capture has no focus ring activated. Browser viewport override is reset for handoff.
- Full-view combined comparison: `qa/comparison-final.jpg` (source left, implementation right).
- Focused combined comparisons: `qa/comparison-hero.jpg` and `qa/comparison-reader.jpg`. Both were opened and reviewed after the final capture.
- Mobile evidence: `qa/mobile-home.png` and `qa/mobile-install.png`, 390 × 844. Mobile content width checked at 390; no horizontal page overflow. Guide nav scrolls horizontally inside its own region.
- Supplemental states: `qa/example.png`, `qa/guide.png`, `qa/install.png`.

## Findings and comparison history

### First comparison — blocked until repaired

Evidence: `qa/desktop-before.png` and `qa/comparison-before.jpg`.

- [P2] Hero padding and vertical rhythm pushed the reader and guide below the intended position. Reduced header/hero spacing at the source breakpoint, adjusted heading line height and increased heading size to match the two-line hierarchy.
- [P2] Desktop compact menu was visible alongside desktop navigation due to CSS declaration order. Restricted it explicitly to the mobile breakpoint.
- [P2] Guide gateway CTA fell below the source frame. Reduced step/gateway spacing and topic icon sizes at the reference breakpoint, preserving the CTA and all topics.
- [P2] Installation dialog lacked an accessible name. Added `aria-labelledby="install-heading"`; verified the named dialog is visible, dismissible with Escape and usable at 390 px.

### Final comparison — passed

Evidence: `qa/desktop-final.png` and `qa/comparison-final.jpg`, plus the two focused comparisons. No actionable P0/P1/P2 findings remain. Hero, reader, three-step workflow and six-topic guide entry follow the selected layout and hierarchy; lower sections extend it into the requested working page.

## Required fidelity surfaces

- Fonts/typography: Noto Sans TC with system fallbacks, bold two-line display heading, restrained monospace eyebrow, readable body text and consistent heading hierarchy. Minor optical differences from raster-generated lettering are expected.
- Spacing/layout: centered hero, paired CTAs, wide reader preview, three-column workflow and six-topic gateway aligned to the source. Responsive navigation, stacked demo panels and horizontal guide navigation checked on mobile.
- Colors/tokens: white/pale blue base, blue primary action, dark ink headings and yellow/blue annotation accents. Secondary text darkened for readability. The source's decorative soft backdrop is simplified; no CSS-drawn image asset substitutes are used.
- Image quality: dedicated generated reader illustration, 1586 × 992 original pixels, saved at `public/assets/reader-preview.png`; displayed without distortion. It retains the three columns and annotations. Visible caption identifies it as an illustration, not a real screenshot or interactive app. Standard icons come from Phosphor.
- Copy/content: hero and gateway preserve the selected Traditional Chinese concept. Ten guide topics and file/dialogue examples come from the project's authored help. Local-only return navigation is excluded. Added explicit product-site context and repository-publication prerequisite. No invented testimonials, pricing or usage statistics.

## Primary interactions tested

- Navigation anchors and guide gateway open the correct section.
- Install CTA opens the named dialog; close and Escape work, including mobile.
- Copy action resolves and displays its success status. Browser clipboard bridge returned an empty string, so pasted clipboard content was not independently verified; failure status and manual selection fallback are provided.
- All three example tabs change source/prompt/highlights/KWIC. Arrow-key tab navigation updates selected state.
- Clicking the 火攻 annotation updates KWIC; the 詞夾子 tab selects 周瑜.
- Guide topics switch to the correct help content; vocabulary CSV and DocuXML export instructions verified.
- FAQ expands to show the correct answer.
- Mobile menu opens, guide navigation works, menu closes after selection.
- Image loads successfully; document width matches viewport at desktop and mobile.
- Browser console checked: no captured errors or warnings.
- Production build passed. Four bundled Sites worker/packaging checks passed. No deployment performed.

## Follow-up polish (P3)

- Generated illustration differs slightly in intrinsic proportions and line breaks from the source mock. It is noninteractive marketing media; the actual interactive example is directly below.
- Full browser/screen-reader certification and real remote installation are outside this preview. Repository publication remains a prerequisite.

## Implementation checklist

- [x] Preserve the selected third visual direction.
- [x] Provide functional primary actions and mobile navigation.
- [x] Import the existing help into a reusable guide content file.
- [x] Separate product content and document how to reuse it.
- [x] Complete combined visual and focused-region comparisons.
- [x] Build and check the final local project.
