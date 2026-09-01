# Paper Diorama Prompt System

A repeatable system for writing AI video prompts in the "aged-print collage, deep 3D diorama" style.

---

## 1. Structure

Every prompt has two blocks:

```
[STYLE BLOCK]  — fixed, pasted identically every time
SHOT:          — variable, rewritten per clip
```

The style block never changes. All creative variation lives in the SHOT.

---

## 2. The Style Block (copy verbatim)

> Use the attached style sheet for materials only – aged-print collage textures, halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, print grain. Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama – cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus – one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. ALERT WASH means the entire frame floods to the hot accent tone in one beat. Motion: springs with overshoot, staggered entrances, ticking counters. Audio: sound design only – paper pops, whooshes, stamps, ticks. No music. No voice-over.

### Why each clause exists (do not delete these)

| Clause | Job |
|---|---|
| "style sheet for materials only" | Borrow texture, not layout |
| "Do NOT copy the sheet's layout or its flatness" | Kills the #1 failure mode: flat 2D output |
| "deep 3D paper diorama / physical layers in real space" | Forces parallax and depth |
| "shallow depth of field / foreground crossing the lens" | Sells the 3D lie |
| "camera is an actor / one committed move" | Prevents mushy multi-move drift |
| "Backgrounds change per clip" | Stops every shot looking identical |
| "ALERT WASH" | Defines a reusable named beat |
| "springs with overshoot, staggered, ticking" | Motion signature |
| "sound design only, no music, no VO" | Audio lock |

---

## 3. The SHOT Formula

Write in this exact order. Two to five sentences. No headers, no bullets.

```
Background: [what + how far + focus state].
FG: [elements] snap/slide/drop in at [different depths].
[Connective action: arrow draws, counter ticks, chip races, stamp lands].
Camera [ONE move], focus [racking behaviour].
Settle [where].
```

### Slot menus

**Background** — pick one, out of focus, tilted in perspective
faded world map · torn ledger page · newspaper column wall · blueprint grid · stock chart engraving · passport stamp field · circuit trace print · topographic map · index-card wall · shipping manifest

**Foreground elements**
cards · torn strips · logo plates · giant stat number · halftone cutout person · coin chips · arrows · stamps · pins with thread · folder tabs · ticker tape

**Depth cue (mandatory)** — always state layers explicitly
"at three different depths" · "one near the lens, two deep" · "stacked receding into the frame" · "the nearest whipping past the lens with motion blur"

**Camera move — pick exactly ONE**
orbits a quarter turn · flies between two layers · dives from above · whips left to right · pushes in through a torn hole · pulls back to reveal · cranes up over the stack · racks focus front to back

**Settle**
mid-orbit · on the number · on the closing loop · on the cutout's face · wide on the full diorama

---

## 4. Rules

1. **One camera move per clip.** Two moves = mush.
2. **Always name at least two depths.** If depth isn't stated, the model flattens it.
3. **Logos stay flat and unmodified.** State this when logos appear.
4. **Numbers are giant.** Stats are set dressing, not captions.
5. **End with a settle.** Gives the clip an out point.
6. **Change the background every clip.** Same palette, new surface.
7. **Present tense, active verbs.** "snap in," "draws," "races," "whips."
8. **No stage-direction tags, no shot numbers, no timecodes.**

---

## 5. Named Beats (reusable vocabulary)

- **ALERT WASH** — entire frame floods to the hot accent tone in one beat
- **STAMP** — an approval/rejection stamp slams in at foreground depth, dust puff
- **TICK-UP** — a giant number counts up with overshoot then settles
- **TEAR** — a paper layer rips to reveal the layer behind it
- **THREAD PULL** — pins and red thread draw a connection between two cutouts

Define new beats in ALL CAPS in the style block once, then call them by name in the SHOT.

---

## 6. Reference Example

**SHOT:** Background: a faded world map tilted in perspective, far out of focus. FG: three cards snap in at different depths forming a triangle, each carrying one attached logo – Nvidia, OpenAI, Microsoft – flat, unmodified. A thick arrow draws card-to-card into a closed loop; coin chips race along it, the nearest whipping past the lens with motion blur. Camera orbits the triangle a quarter turn, focus racking card to card. Settle mid-orbit.

### Variations built from the formula

**SHOT:** Background: a torn ledger page tilted away, deep out of focus. FG: a giant stat number 47% drops in close to the lens, halftone cutout of a worker standing small behind it. Counter ticks up from 12% with overshoot; torn strips flutter past at foreground depth. Camera pushes in through the gap beside the number, focus racking from strips to the cutout's face. Settle on the number.

**SHOT:** Background: a newspaper column wall, receding, fully soft. FG: six index cards stacked at staggered depths, red thread pinned between three of them. THREAD PULL snaps the connection taut, dust lifting off the paper. ALERT WASH on the snap. Camera whips left to right past the near cards, focus racking front to back. Settle wide on the full diorama.

---

## 7. Quick Checklist

- [ ] Style block pasted verbatim, unedited
- [ ] Background named, tilted, out of focus
- [ ] At least two depths explicitly stated
- [ ] Exactly one camera move
- [ ] Focus behaviour described
- [ ] Settle stated
- [ ] Background differs from the previous clip
- [ ] No music, no VO, no stage directions
