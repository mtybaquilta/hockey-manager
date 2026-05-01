# Phase 2: Better Game Sim

## Goal

Improve hockey realism while keeping the existing architecture and UI mostly intact.

## In Scope

### Period-aware simulation
- 3 periods, 60 ticks per period, 180 regulation ticks
- Period derivable from tick (overtime = period 4)
- Each event records its period

### Penalties
- Small per-tick chance of a penalty against the currently on-ice attacking line
- Penalty duration in ticks (no named types yet)
- Deterministic from the game seed
- No 4-on-4 complexity yet (collapsed to even strength)

### Power play effects
- Team on power play: increased shot probability, slight goal-probability bump
- Shorthanded team: reduced shot probability
- Goals tagged EVEN / PP / SH

### Goalie game-form variance
- Per-game form offset, deterministic from the game seed and goalie id
- Goalie `mental` reduces variance amplitude
- Form affects save probability for that game only

### Gameplan / Tactics — IMPLEMENTED
- Per-team gameplan with two axes: `style` (balanced / offensive / defensive / physical) and `line_usage` (balanced / ride_top_lines / roll_all_lines).
- Style modifiers tilt shot probability, defensive suppression, shot quality, and penalty rates (see `sim/constants.py:GAMEPLAN_STYLE_MODIFIERS`).
- `line_usage` controls forward and defense TOI distribution across lines/pairs (see `sim/constants.py:LINE_USAGE_*_DISTRIBUTION`).
- Auto-selected PP / PK units (3F+2D / 2F+2D), purely a function of lineup attributes — no UI.
- Verified with `sim/tools/run_gameplan_split_report.py`: style modifiers move GF/GA/SF/SA/PEN in the expected directions; `line_usage` shifts top-six vs bottom-six point share without breaking league SH% / goals-per-game.
- Shooter-selection weight flattened to `100 + shooting` so elite shooters still lead but don't run away with shot volume; verified with `sim/tools/run_scoring_report.py`.

## Out of Scope (Phase 2)
- Special teams lineup UI
- Injuries
- Detailed faceoffs / zones / play-by-play
- Tactics UI (the gameplan model is in the sim; surfacing it in the UI beyond what already ships is deferred)
- Trades, contracts, draft, scouting, multi-season, auth
- Major UI work
