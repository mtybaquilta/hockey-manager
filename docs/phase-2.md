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

## Out of Scope (Phase 2)
- Special teams lineup UI
- Injuries
- Detailed faceoffs / zones / play-by-play
- Tactics UI
- Trades, contracts, draft, scouting, multi-season, auth
- Major UI work
