# 0810 Editorial Revision Design

## Goal

Repair the rendered 0810 edit using the user's frame review while preserving
the original narration, verified evidence, internet-license provenance, and
human final-approval gate.

## Caption design

- Use `outlined-demo` for all continuous captions in this edit.
- Position captions at a new `lower-82` safe anchor.
- Render phrases at 58 px with a strong dark stroke.
- Keep most words white and statically emphasize one meaningful word per page
  in lime-yellow.
- Do not use active-word timing, karaoke scaling, or animated recoloring.

## Visual timing

- Keep the hook on presenter, but move the baked hook card below the detected
  face area.
- Change the ATC evidence beat from one still into:
  1. official page overview;
  2. source-derived proof macro with a restrained punch-in.
- Show the UPI payment clip and UPI logo from the spoken `UPI` onset at
  15.14 seconds.
- Switch to robot footage at the spoken comparison `vaise trading robots`
  around 17.26 seconds.
- Hold an active tablet/trading clip through the complete `buy sell clicks
  kam karenge` clause from 19.84 to 23.36 seconds.
- Show official robot-action evidence during `robots multiple pairs scan`,
  then moving market footage during `orders execute`.
- Align the supplied Profit Bricks logo to the spoken brand name at
  36.44 seconds.

## Assets and evidence

- Use the user-supplied green/gold Profit Bricks Forex Automation logo.
- Keep all existing official MQL5/MetaTrader captures and licensed Mixkit
  provenance.
- The ATC proof macro must contain only pixels derived from the official
  MetaTrader source capture.
- Do not add Flow or other generated footage.

## Verification

- Regression tests cover shot boundaries, caption family/anchor/highlight,
  hook alpha bounds, UPI timing, ATC proof motion, and logo timing.
- Render and inspect the exact hook, ATC, UPI, fewer-clicks, brand, and CTA
  frames.
- Preserve 1080x1920 H.264/AAC, dialogue continuity, loudness, and
  `awaiting-final-approval`.
