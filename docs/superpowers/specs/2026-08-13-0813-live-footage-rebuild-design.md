# 0813 Live-Footage Rebuild Design

## Objective

Replace the artificial full-screen evidence cards, document crops, and
dashboard-style diagrams in the 0813 edit with visually attractive real
moving footage. Preserve all verified facts, narration, captions, timing, and
audio quality.

## Locked visual direction

- Full-frame live footage is the default.
- Presenter footage is used for short connective resets.
- Exact numbers may appear as small, clean overlays only when already
  supported by `evidence.json`.
- No full-screen webpages, source documents, synthetic dashboards, outlined
  information cards, or dark HUD-style diagrams.
- No AI-generated software interfaces or factual evidence.
- Source attribution remains in the production artifacts and may appear as a
  discreet micro-source line when an exact factual claim is visible.
- Shots must contain visible movement; static photos are allowed only with a
  meaningful crop change and when no suitable video exists.

## Shot replacements

| Existing shots | Existing problem | Replacement |
|---|---|---|
| 4–5 | BLS webpage and synthetic `CPI-U / BASKET` card | Moving supermarket aisle, shopping cart, checkout scanner, or receipt footage. Add only a small `CPI = HOUSEHOLD BASKET` label. |
| 10–13 | Full-screen monthly/yearly evidence graphics | Checkout/receipt/price-tag macros. Reveal verified `0.1% MONTHLY` and `3.4% YEARLY` as restrained overlays over motion. |
| 15–16 | Synthetic actual-versus-forecast and three-factor dashboard | Real market screen followed by a three-shot live montage: gas station, apartment/rent, and trader/rates footage. |
| 19–20 | Energy table and gasoline-number cards | Real gasoline pump/station action with small `ENERGY −1.5%` and `GASOLINE −2.9%` labels. |
| 23 | Shelter evidence card | Moving apartment exterior/interior or rent-key footage with `SHELTER ≈ TWO-THIRDS` as a minimal overlay. |
| 24–25, 27, 29 | CNBC/document cards and rate card | Real trading desk, price chart, keyboard, and market-reaction footage. Use short claim labels instead of article screenshots. |
| 32–35 | Automation guardrail cards | Presenter/trader/product-action footage with one short label per beat: `SPREAD LIMIT`, `PAUSE`, `CONFIRMATION`. |
| 36–37 | Headline and full-release document screens | Live market footage followed by a presenter reset showing the final lesson. |

## Asset policy

1. Reuse the strongest already-reviewed Pexels and Mixkit clips where they
   match the narration.
2. Source additional licensed live clips for checkout scanning, receipts,
   grocery prices, and market reaction only when current assets are
   insufficient.
3. Reject watermarks, artificial text, visibly generated footage, irrelevant
   UI, weak portrait crops, and clips without meaningful movement.
4. Save provider, creator, source URL, license URL, local path, and SHA-256
   checksum for every selected asset.

## Motion and typography

- Use hard cuts, punch crops, tracked reframes, and occasional speed ramps.
- Keep the established compact captions and protect faces/products.
- Factual overlay size should remain subordinate to the footage.
- One primary subject and one visual action per shot.
- No decorative particles, global grain, floating icons, or constant zoom.

## Audio

- Preserve the approved narration master and all words.
- Preserve the approved documentary music and eight semantic SFX.
- Remap sound accents only if a changed visual boundary requires it.
- Retain the existing loudness, true-peak, continuity, and speech-protection
  gates.

## Acceptance

- None of the rejected five visual treatments remains in the final video.
- No full-screen synthetic evidence card or document page remains.
- At least 80% of the replacement interval consists of live moving footage.
- Every exact visible number remains supported by `evidence.json`.
- Captions remain readable and collision-free.
- Full decode, 100% narration retention, reference pacing, audio alignment,
  color, and composition gates pass.
- Final contact sheet is visually reviewed before delivery.
