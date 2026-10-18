# Audience screen revamp: "Borderless Night" (design spec)

Date: 2026-10-17 · Owner of `screen/`: Austin (agreed to this rewrite) · Driven by: Harvey
Goal: win Paper's "Best Designed Hack" at LA Hacks (judged on design fundamentals, ease of use,
and personal craft that doesn't look AI-generated). Feature freeze 2026-10-18 10:00 PT.

## 1. Context

- **Story.** Our team went to teamLab in Tokyo and loved art you are immersed in: works that react to
  people and flow between rooms. Blind visitors can't take part. This project lets them feel a painting.
- **Audience of this screen.** Sighted judges and passers-by at the demo table (laptop 1440×900 and an
  external monitor 1920×1080). The blind visitor never sees it; it shows what they hear and feel.
- **Research.** 147 Mobbin references across 9 sections: `docs/design/inspiration.md`, images in
  `docs/design/inspo/`. Codes like `V01` below point into that log.
- **Direction chosen.** A, "Borderless Night" (dark teamLab room, light as hierarchy, art flows from the
  painting into the board), with the typographic discipline of B, "Wall Label". Rejected: B on its own
  (less immersive), C "Pin Art" (kitsch risk, painting loses the spotlight).

## 2. Layout and scenes

One continuous dark canvas. No cards. Designed at 1920×1080, scales to 1440×900 with `clamp()`, fits a
1280×720 projector with no scrolling (`max-height: 800px` tightening), stacks below 1100px wide.

```
TopStrip:   [wordmark]                                  ● LIVE 03:12   [S] AGENTS
Left 58%:   Room glow + PaintingStage (Spotlight, part tag) + Placard (artist / title / year)
Right 42%:  Board (giant outline numeral behind, NOW TOUCHING · 02 / 06, part name, location)
            Captions (last 4 lines, newest largest) with SpeakingIndicator
Bottom:     TourRail (one ball per part)
Overlay:    AgentDrawer from the right, toggled with S, closed by default
```

| Scene | Condition | Content |
|---|---|---|
| offline | `online === false` | IdleScreen, dimmed: "The guide is on a break. Start main.py to open the gallery." |
| looking-up | online, no painting, `activity.gemini.status === "working"` | empty frame with a dashed outline sweeping it, the Gemini detail line ("Finding the parts of …"), board balls breathing |
| idle | online, no painting | IdleScreen: the 4 demo shapes cycle on the board, headline "Some art is meant to be touched.", hint "Say \"Show me the Mona Lisa\"", footer "Best experienced with your hands." |
| touring | painting present | full layout above (section may be null right after load: board shows all wells empty) |

Narrow (<1100px): painting, board, captions and rail stacked. Reduced motion: every animation becomes a 200ms opacity fade.

## 3. Design system "Lantern Water"

Mood: the water room at teamLab Planets lit by lanterns. Every colour is an object in that room.

### Colour tokens

| Token | Hex | Object | Role |
|---|---|---|---|
| `--color-ink` | `#08090B` | black water | page background |
| `--color-stone` | `#131518` | wet stone | drawer, raised surfaces |
| `--color-stone-2` | `#1C1F23` | stone edge | hairlines, empty ball wells |
| `--color-paper` | `#F2EADC` | lantern paper | primary text (16.7:1 on ink) |
| `--color-paper-dim` | `#B4AB9C` | paper in shadow | secondary text (8.8:1) |
| `--color-paper-faint` | `#7E776D` | | decoration and ≥24px text only (4.5:1) |
| `--color-lantern` | `#FFB547` | lantern flame | the single accent: "now" (current part, live dot, spotlight edge) |
| `--color-moss` | `#8CC48A` | moss | DONE (drawer only) |
| `--color-koi` | `#FF6B4A` | koi | FAILED (drawer only) |

Rules:
- One intense colour moment: lantern marks only what is happening now.
- Status is never colour-only; every status has a word.
- Painting-derived colour:
  - The room glow uses the painting's average colour at 12% opacity over ink.
  - Each raised ball uses the average colour of its own cell inside the section bbox, with its HSL
    lightness raised to at least 55% so it glows on ink.
  - If the image can't be read, use lantern.

### Type tokens (self-hosted via @fontsource, bundled in dist)

| Token | Family / style | 1920 | 1440 | Use |
|---|---|---|---|---|
| `--text-numeral` | Instrument Serif, outline (`-webkit-text-stroke` 1px paper-faint, transparent fill) | 360 | 270 | part number behind board |
| `--text-display` | Instrument Serif 400, leading 1.0, tracking −0.02em | 80 | 60 | painting title, idle headline |
| `--text-title` | Instrument Serif 400 | 48 | 36 | current part name |
| `--text-kicker` | Instrument Serif Italic | 28 | 22 | artist, kickers |
| `--text-caption-now` | Instrument Sans 500, leading 40/32 | 30 | 24 | newest spoken line |
| `--text-body` | Instrument Sans 400, leading 30/26 | 20 | 17 | older lines, descriptions |
| `--text-label` | JetBrains Mono 500, uppercase, +0.14em | 14 | 13 | labels; 13px is the floor |

Fallbacks: `Georgia, serif` / `system-ui, sans-serif` / `ui-monospace, monospace`.

### Space, shape and motion

- Spacing: `--spacing-1..10 = 4 8 12 16 24 32 48 64 96 128` px. Column split 58/42, gutter 96, outer margin 64
  (scaled with clamp).
- Shape: only circles and 1px `stone-2` hairlines. No cards, no rounded panels, no drop shadows; light
  (glow) is the only depth. One hand-made mark: the spotlight tag's hook is a hand-drawn SVG stroke.
- Motion tokens:
  - `--ease-rise: cubic-bezier(.34,1.56,.64,1)`
  - `--ease-light: cubic-bezier(.22,1,.36,1)`
  - `--dur-ball: 400ms`, `--stagger-row: 70ms`, `--dur-spot: 600ms`, `--dur-flow: 900ms`,
    `--dur-ripple: 1600ms`, `--dur-idle: 8s`, `--dur-fade: 200ms` (reduced motion).

### Voice
Copy reads like a museum placard: "Now touching", "The guide is on a break.", "Best experienced with your
hands." Never "Status: OK", "Section loaded" or "AI-powered". All strings live in `design/copy.ts`.

## 4. Components

| Component | Shows | Props / data |
|---|---|---|
| TopStrip | wordmark (`WORDMARK` in copy.ts) · live dot + LIVE + session timer (mm:ss from first time online in this tab) · `[S] AGENTS` button | `online`, drawer open/close |
| Room | blurred painting, tinted with its average colour, behind everything | `painting.image`, average colour |
| PaintingStage | image fitted in the left column | `painting.image`, `title` |
| Spotlight | dims outside the bbox, 1.5px lantern edge, glides between parts; tag `02 · HER HANDS` hung on a hand-drawn hook at the bbox corner (flips side when the bbox touches the edge) | `section.bbox`, `number`, `name` |
| Placard | artist (kicker italic) / title (display) / year (label) | `painting` |
| Board | 10×10 wells (`stone-2`); raised balls in painting colours with glow; outline numeral; `NOW TOUCHING · 02 / 06`; part name; location as `TOP CENTER OF THE CANVAS`; corner badge `SIMULATED` or `MIRRORED LIVE` | `section`, `hardware`, `painting.sections.length`, cell colours |
| BorderlessFlow | the signature transition (below) | previous and next section, element refs |
| Captions | last 4 transcript lines: newest `caption-now` in paper, the 3 older step down to `body` and fade to paper-dim; mono speaker label GUIDE / VISITOR | `transcript` |
| SpeakingIndicator | ring of 8 dots next to the newest line's label: **speaking** (rings ripple outward) while the newest line changed <4s ago; otherwise **thinking** (dots orbit) while `activity.gemini` is `working` (not Creao/Browser Use: they run in the background for minutes); otherwise **listening** (slow breathe) | output of `useSpeaker` |
| TourRail | one ball per section in tour order with mono name below: visited = paper-dim filled, current = lantern + halo, upcoming = hollow `stone-2` ring | `painting.sections`, `section.number`, visited set |
| AgentDrawer | slides over the right column (`stone` surface, layout never reflows). Rows: status dot + WAITING/WORKING/DONE/FAILED word, sponsor, job, detail in mono. Last row "On the wire": `section.frame` in mono | `activity`, `section.frame` |
| IdleScreen | the board cycles the 4 demo signature grids (8s each, balls in lantern), headline, hint, footer; offline variant dims and swaps copy | `idleShapes.ts`, `online` |

Sponsor names and jobs (kept from the current ActivityBar):
- ElevenLabs: voice guide
- Gemini: finds the parts and draws each shape
- Creao: Tactile Tour Writer agent
- Browser Use: reads the museum's website

### Signature interaction: Borderless flow
When `section.number` changes:
1. The spotlight glides to the new bbox (`--dur-spot`).
2. A faint 10×10 grid fades in over the bbox only. Cells that are 1 in `section.grid` light up in lantern.
3. Each lit cell becomes a dot that flies (transform translate + scale, `--dur-flow`, `--ease-light`) to its
   well on the board. The positions come from `getBoundingClientRect` of the bbox cells and the wells.
4. On arrival the balls rise row by row (`--dur-ball`, `--stagger-row`, `--ease-rise`) and take their
   painting colour.

At most 100 absolutely positioned dots, CSS transforms only, no library. Skipped (balls just fade in) when
reduced motion is on, the measurements are missing, or it is the first section after a painting loads
(nothing to fly from yet: the grid lights and the balls rise in place).

## 5. Code architecture (`screen/src/`)

```
main.tsx            fonts + design/tokens.css
App.tsx             scene selection, drawer state (S key + button), passes props
types.ts            unchanged
useScreenState.ts   unchanged
design/tokens.css   all tokens in §3 (names identical to the Paper file's tokens)
design/copy.ts      every visible string + WORDMARK
lib/colors.ts       pure: averageColor, cellColors(bbox), lift, css (tested)
lib/speaker.ts      pure: speechState → 'speaking' | 'listening' | 'thinking' (tested)
lib/visited.ts      pure: visit() → section numbers shown for the current painting (tested)
lib/flow.ts         pure: shouldFly(prev, next) (tested)
lib/scene.ts        pure: pickScene(state, online) (tested)
lib/format.ts       pure: pad, formatClock (tested)
lib/grid.ts         pure: normalizeGrid → always 10×10 of 0/1 (tested; keeps commit 5066f10's rule)
lib/idleShapes.ts   4 grids copied from cache/*.json (section 1 of each demo painting)
lib/motion.ts       reducedMotion()
lib/hooks.ts        React hooks: usePaintingPixels, useSpeaker, useVisited, useFlow, useSessionClock
components/<Name>.tsx + <Name>.css for each component in §4 (+ BallGrid, LookingUp)
test/*.test.ts      node:test files for the pure lib modules, run with `npm test` (Node 24 strips types; no new dependency)
```

Deleted: `components/PaintingView.tsx`, `Transcript.tsx`, `ActivityBar.tsx`, `styles.css` (split into
tokens and per-component CSS).

New dependencies: `@fontsource/instrument-serif`, `@fontsource-variable/instrument-sans`,
`@fontsource-variable/jetbrains-mono`. No other runtime dependencies.

Not changing: `screen.py`, the `/api/state` JSON, `test_screen.py`, the `vite.config.ts` proxy.

### Failure handling
- Image fails to load: hidden (blank frame, no broken-image icon). Canvas tainted: lantern colours, no crash.
- Malformed grid (short rows, junk values): drawn as a clean 10×10 of 0/1.
- `painting.image` null: placard and board without a picture.
- Fonts fail: fallback stacks.
- Flow measurements missing: fade-in.
- main.py stops: offline scene, then resume.
- An unknown activity key is ignored.

## 6. Paper deliverables

New Paper file "ArtForAll — Design", one page per item:
1. **Story**: teamLab, the problem, the audience.
2. **Research**: 12–15 STRONG references with take/leave notes, the 7 patterns, the 3 directions and the choice.
3. **Design system**: Paper tokens identical to tokens.css, swatches with scene objects and contrast ratios,
   type specimen, spacing, shape, motion, voice.
4. **Components**: every state of every component in §4.
5. **Screens**:
   - idle, offline, looking-up;
   - touring (Mona Lisa and The Starry Night);
   - touring with the drawer open;
   - 1440×900 and narrow layouts.
6. **Borderless flow**: 4-frame storyboard.

Exports (PNG per page plus a combined PDF) go to `docs/design/paper/`.

## 7. Documents

- This spec.
- `docs/design/inspiration.md` (done).
- `docs/design/design-decisions.md`, for Devpost readers:
  - the story;
  - judging criteria mapped to decisions;
  - process and patterns;
  - directions and the choice;
  - each design-system decision with its reason and inspiration codes;
  - accessibility;
  - what was left out;
  - before/after screenshots;
  - a ready-to-paste Devpost "Design" section.

## 8. Testing and done criteria

- `cd screen && npm test` passes (node:test on the pure lib modules).
- `cd screen && npm install && npm run build` passes (tsc + vite). The rebuilt `dist/` is committed.
- `python test_screen.py` passes unchanged.
- `python screen.py --demo` screenshots (Playwright):
  - each scene at 1920×1080 and 1440×900;
  - narrow at 400px;
  - reduced motion.

  Each is compared side by side with the Paper screens.
- Text contrast meets the §3 ratios. No text smaller than 13px. No horizontal scroll at any width.
- With main.py stopped, the page shows the offline scene within one poll cycle and recovers on restart.

## 9. Out of scope

Clicking to change parts, settings, a theme toggle, a light mode, backend or contract changes, the final
.
