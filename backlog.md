


# Hockey Manager — Overall Backlog

## Purpose

This backlog captures both near-term scope and long-term ideas for the hockey management/simulation game.

It is broader than the current active scope. Items listed here are not automatically approved for implementation. The goal is to preserve ideas, organize priorities, and make future planning easier.

---

## Current State

Implemented foundation:

- Core season loop
- Event-driven match simulation
- Box scores
- Schedule and standings
- Stats hub
- Player detail pages
- Multi-season progression
- Player development
- Gameplans/tactics
- Lineups
- Season rollover
- Development history

Main missing pillar:

> **Roster agency** — the user needs more meaningful ways to change and shape the team.

Right now the user can inspect, set lineups, set gameplan, advance, and watch development. The next big gameplay leap should let the user actively improve or reshape the roster.

---

# Priority 0 — Immediate Polish / Clarity

These should happen before adding large roster systems. The user needs to understand player quality clearly before signings, releases, trades, contracts, or draft picks become meaningful.

---

## P0.1 Redesign My Team Page Around Player Quality

### Goal

Make it obvious who is good, who has potential, and who matters.

### Why It Matters

The current team page shows a lot of data, but it does not immediately answer:

- Is this player good?
- Is he good for his age?
- Is he one of my best players?
- Is he a prospect or just depth?
- Should I care about replacing him?

Before roster-building mechanics are added, the user must be able to evaluate players quickly.

### Notes

The current page feels too much like a raw roster spreadsheet. OVR should be the main visual anchor. POT should be visible because player development now exists. Role and archetype labels would make the roster much easier to scan.

### Suggested Tasks

- Make OVR visually prominent.
- Show POT on roster rows.
- Add role labels:
  - Star
  - Top Line
  - Top Six
  - Middle Six
  - Depth
  - Prospect
  - Starter
  - Backup
- Add archetype labels:
  - Sniper
  - Playmaker
  - Two-Way Forward
  - Power Forward
  - Defensive Forward
  - Offensive Defenseman
  - Stay-at-Home Defenseman
  - Starter Goalie
  - Backup Goalie
- Add team summary cards:
  - Best Player
  - Best Prospect
  - Team Avg OVR
  - Team Avg Age
  - Team Identity
- Add sorting by:
  - OVR
  - POT
  - Age
  - Position
- Consider replacing full raw attribute columns with:
  - Role
  - Archetype
  - Key strengths
  - Key weakness

### Suggested Roster Columns

    PLAYER | POS | AGE | OVR | POT | ROLE | PROFILE

Example:

    Caleb Gadd | C | 20 | 70 | 81 | Top Prospect | Playmaker · PS 77 · SH 73

---

## P0.2 Redesign Player Page Into a Player Dossier

### Goal

Make the player page answer “is this player good?” immediately.

### Why It Matters

The player page currently contains useful information, but the hierarchy is weak. OVR, POT, role, development type, and context should be much more prominent.

The page should feel like a player dossier, not just a stats dump.

### Notes

The first screenful should clearly summarize the player:

- Current quality
- Future potential
- Role on the team
- Archetype
- Strengths
- Weaknesses
- Development trend

### Suggested Tasks

- Add a large OVR hero card.
- Add POT next to OVR.
- Show development type.
- Show role and archetype.
- Add a one-line player summary.
- Add team rank and position rank.
- Add strengths and weaknesses.
- Add development trend.
- Move game log lower on the page.

### Example Header

    Caleb Gadd
    C · Age 20 · Visby Voyagers

    70 OVR · 81 POT
    Top Prospect · Late Bloomer · Playmaker
    #4 on team by OVR · #1 under-23 player

    Strong young center with high upside and good current production.

### Suggested Page Order

1. Player hero
2. OVR / POT / role / archetype
3. Season summary
4. Team and position context
5. Strengths and weaknesses
6. Development history
7. Game log

---

## P0.3 Document Sim-Tuning Known Issue

### Goal

Preserve the investigation around top-line concentration and gameplan stacking.

### Why It Matters

The league-level sim is mostly healthy, but there is a known edge case where offensive + ride_top_lines can create excessive top-line scoring concentration.

This should be documented so future tuning does not start from scratch.

### Suggested File

    docs/sim-tuning-notes.md

### Notes to Include

- Offensive + ride_top_lines can create top-line scoring concentration.
- UME example: a 75/73/73-ish top line produced extreme totals.
- Global league scoring metrics were healthy.
- Do not globally lower scoring to fix this.
- Future fix should target line/gameplan concentration.
- Possible future levers:
  - soften ride_top_lines further
  - add offensive + ride_top_lines stacking limiter
  - reduce L1 share target
  - analyze persisted seasons with DB-backed tool

### Status

Parked. Do not continue tuning unless it repeatedly affects real seasons.

---

# Priority 1 — Roster Agency Phase

This is the most important next gameplay layer.

## Core Goal

Let the user improve or reshape their team without adding full contracts, trades, draft, or salary cap.

Current gameplay lets the user inspect and optimize internally. Roster agency lets the user act externally:

    Inspect weakness → find player → sign/release → adjust lineup → sim → evaluate result

---

## P1.1 Free Agent Pool

### Goal

Let the user find players outside their team.

### Why It Matters

This is the smallest useful roster-building mechanism. It gives the user a way to improve weak roster spots without needing trades, contracts, scouting, or draft.

### Suggested Scope

- Generate free-agent skaters and goalies.
- Add `/free-agents` page.
- Show:
  - OVR
  - POT
  - Age
  - Position
  - Role
  - Archetype
  - Key attributes
- Allow filtering by:
  - Position
  - Player type
  - Minimum OVR
  - Minimum POT
- Allow sorting by:
  - OVR
  - POT
  - Age
  - Position

### Implementation Option

Use nullable team IDs:

    skater.team_id nullable
    goalie.team_id nullable

Players with `team_id = null` are free agents.

### Out of Scope First Pass

- Salaries
- Contract negotiation
- Bidding
- AI competition
- Waivers
- Salary cap

---

## P1.2 Sign Player

### Goal

Allow the user to add a free agent to their team.

### Suggested API

    POST /api/free-agents/skaters/{id}/sign
    POST /api/free-agents/goalies/{id}/sign

### Tasks

- Validate that the player is a free agent.
- Validate that the user controls the destination team.
- Validate roster size.
- Set `team_id` to the user team.
- Invalidate roster and free-agent queries.
- Return updated roster/free-agent state if useful.

### UX Notes

- Add a Sign button.
- Use confirmation modal:
  - “Sign Caleb Gadd?”
- Show toast:
  - “Signed Caleb Gadd.”
- If roster is full, show:
  - “Roster full. Release a player first.”

---

## P1.3 Release Player

### Goal

Allow the user to remove players from the roster.

### Suggested API

    POST /api/players/{id}/release

or split by type:

    POST /api/skaters/{id}/release
    POST /api/goalies/{id}/release

### Tasks

- Validate that the player belongs to the user team.
- Prevent release if roster would fall below valid minimum.
- Prevent release if player is currently in the lineup, or require removal first.
- Set `team_id = null`.
- Invalidate roster and free-agent queries.

### First-Pass Rule

If the player is in the lineup, block release with a clear error:

    Remove this player from the lineup before releasing him.

This is simpler than auto-repair.

---

## P1.4 Roster Limits

### Goal

Make sign/release meaningful.

### Suggested Rules

Minimum valid team:

- 12 forwards
- 6 defensemen
- 2 goalies

Maximum roster:

- 23 players

### Tasks

- Add roster validation service.
- Show roster count on My Team page.
- Show warnings if roster is invalid.
- Block advancing if user lineup is invalid.
- Keep AI rosters valid through default generation.

### Notes

Roster limits create a real decision: signing a player may require releasing another.

---

## P1.5 Free-Agent Comparison UI

### Goal

Help the user decide whether a free agent is worth signing.

### Why It Matters

Without comparison, free agency becomes another data table. Comparison turns it into a decision.

### Suggested Features

For each free agent, show:

- Would rank #X on your team by OVR.
- Would rank #X at position.
- Compared to weakest roster player at same position.
- OVR difference.
- POT difference.
- Age difference.

Example:

    Would rank #5 among your forwards.
    +4 OVR over current 4th-line RW.
    Younger by 6 years.

### Out of Scope

- Trade-value style modeling
- Salary value
- Contract efficiency

---

# Priority 2 — Injuries

Injuries make roster depth matter and give the user reasons to adjust lineups.

---

## P2.1 Basic Injury System

### Goal

Players can miss games.

### Why It Matters

Injuries add consequences and make depth players useful. They also make roster agency more meaningful.

### Suggested Scope

- Small injury chance during games.
- Injury length measured in games.
- Injured players cannot be placed in lineup.
- Injury status shown on roster and player page.
- Basic injury history.

### Data Model

    injury
      id
      season_id
      player_type
      player_id
      start_game_id
      games_remaining
      status active|recovered

### Out of Scope First Pass

- Named body parts
- Detailed severity
- Recurring injuries
- Medical staff
- Day-to-day status
- Long-term injured reserve

---

## P2.2 Injury Lineup Handling

### Goal

Prevent invalid lineups after injuries.

### Options

A. Block advance until user fixes lineup.  
B. Auto-replace injured player with best available valid player.

### Recommendation

For user team:

    Block advance until lineup is fixed.

For AI teams:

    Auto-repair lineup.

### Notes

Blocking the user creates a meaningful management moment. Auto-repair for AI prevents the sim from getting stuck.

---

## P2.3 Injury History on Player Page

### Goal

Add player story and risk.

### Suggested Features

- Current injury status
- Injury history
- Games missed
- Total career games missed

### Example

    Current: Out 3 games
    History:
    - 2027 Season: missed 5 games
    - 2028 Season: missed 2 games

---

# Priority 3 — AI Team Management

Once free agents and injuries exist, AI teams need basic behavior so the league stays believable.

---

## P3.1 AI Lineup Repair

### Goal

AI teams always have valid lineups.

### Suggested Logic

- Fill lineup with highest OVR valid players.
- Respect positions.
- Prefer healthy players.
- Use starter goalie based on OVR.
- Re-run after injuries, signings, releases, and season rollover.

### Notes

This does not need to be smart yet. It only needs to keep AI teams functional.

---

## P3.2 AI Free-Agent Signings

### Goal

AI teams can improve weak rosters.

### Suggested Logic

- Identify weakest roster spots.
- Sign a better free agent if available.
- Respect roster limits.
- Do not sign aggressively every day.
- Prefer younger players when similar OVR.

### Out of Scope First Pass

- Contract bidding
- Cap constraints
- Team strategy
- Rebuild/contender logic

---

## P3.3 AI Gameplan Adjustment

### Goal

Allow AI teams to evolve slightly.

### Suggested Logic

- Offensive teams tend to remain offensive.
- Defensive teams tend to remain defensive.
- Weak defensive teams may shift defensive.
- Physical teams stay physical unless penalty rate is extreme.
- Teams with elite top lines may prefer ride_top_lines.

### Priority

Low. Current generated gameplans are sufficient for now.

---

# Priority 4 — Contracts and Free Agency

Contracts turn free agency into a franchise system.

---

## P4.1 Basic Contracts

### Goal

Players have salary and term.

### Data Model

    contract
      id
      player_type
      player_id
      team_id
      salary
      years_remaining

### Suggested Rules

- Salary generated from OVR, age, and potential.
- Years remaining decreases at season rollover.
- Expired players become free agents.
- User can see expiring players.

### Out of Scope First Pass

- Clauses
- Bonuses
- Arbitration
- Buyouts
- Retained salary
- No-trade clauses
- Salary cap

---

## P4.2 Contract Extensions

### Goal

User can re-sign players before they expire.

### Simple Version

- Player has asking price.
- User can accept or decline.
- No negotiation back-and-forth yet.
- Asking price based on:
  - OVR
  - POT
  - Age
  - Recent performance
  - Position

### UX

- Add expiring contracts page or section.
- Show:
  - current salary
  - years left
  - asking salary
  - asking term

---

## P4.3 Salary Cap

### Goal

Add a roster-building constraint.

### Rules

- Team has cap limit.
- Total active contracts must fit under cap.
- Signing blocked if over cap.
- Extensions blocked if over cap.

### Note

Do this only after contracts work. Salary cap is a complexity multiplier.

---

## P4.4 Offseason Free Agency

### Goal

Create an offseason phase.

### Flow

    Season complete
    → development
    → contracts decrement
    → expired players become free agents
    → free agency phase
    → start next season

### Notes

This would require adding a real offseason state. Do not add until contracts are ready.

---

# Priority 5 — Trades

Trades are fun but dangerous because they require a value model.

---

## P5.1 Player Value Model

### Goal

Estimate player trade value.

### Inputs

- OVR
- POT
- Age
- Position scarcity
- Contract
- Performance
- Development type
- Injury status
- Team need

### Notes

Build this as an internal helper before exposing trade UI.

---

## P5.2 Simple User-Initiated Trades

### Goal

User can offer one-for-one trades.

### First Pass

- One player for one player.
- AI accepts if value is close enough.
- AI rejects if roster would become invalid.
- AI rejects if position need becomes too poor.

### Out of Scope First Pass

- Multi-asset trades
- Draft picks
- Salary retention
- Counteroffers
- Trade block

---

## P5.3 Expanded Trades

### Later Features

- Multi-player trades
- Draft picks
- Salary balancing
- AI counteroffers
- Trade block
- Trade deadline
- Contender/rebuilder logic

---

# Priority 6 — Draft and Prospects

Draft is a major franchise pillar, but it should come after roster agency and contracts start to exist.

---

## P6.1 Draft Class Generation

### Goal

Generate prospects each season.

### Prospect Fields

- Name
- Age
- Position
- Attributes
- Potential
- Development type
- Archetype

### Notes

Prospects can initially be fully visible. Scouting fog can come later.

---

## P6.2 Draft Order

### Simple Version

    Reverse standings order

### Later Version

- Lottery
- Playoff results
- Traded picks
- Compensatory picks

---

## P6.3 Draft UI

### Tasks

- Draft board
- Prospect detail page
- Pick player
- AI picks
- Draft recap

### Notes

This can be a very fun “event” screen, but it is a large feature.

---

## P6.4 Prospect Development

### Later Features

- Unsigned prospects
- Minor league/stash system
- Delayed arrival
- Rights expiration

Not needed initially.

---

# Priority 7 — Scouting

Scouting adds fog-of-war and uncertainty.

---

## P7.1 Hidden Potential

### Goal

User does not see exact POT for unknown players.

### Tasks

- Replace exact potential with range/label.
- Exact potential visible for own players.
- Free agents/prospects show estimated potential.
- Accuracy improves with scouting later.

### Example

    Potential: Top Six
    Range: 76–84
    Risk: Medium

---

## P7.2 Scout Reports

### Goal

Add readable scouting summaries.

### Report Fields

- Potential tier
- Strengths
- Weaknesses
- Risk
- Development type estimate
- Comparable role

### Example

    Projection: Middle-six playmaker
    Strengths: Passing, skating
    Weaknesses: physicality
    Risk: medium

---

## P7.3 Scouting Assignments

### Later Features

- Assign scout to league/region/position.
- Reports improve over time.
- Scouts have accuracy ratings.
- Scouting budget.

---

# Priority 8 — News and Immersion

News makes the world feel alive without necessarily adding complex mechanics.

---

## P8.1 News Feed

### Goal

Generate readable stories from existing events.

### News Types

- Game recap
- Hat trick
- Goalie shutout
- Winning streak
- Losing streak
- Injury
- Development jump
- Signing
- Trade
- Draft pick
- Milestone
- Team clinches top seed

### Notes

This can be template-driven and deterministic.

---

## P8.2 Game Notes

### Goal

Add narrative to box scores.

### Examples

- Won despite being outshot
- Goalie stole the game
- Power play made the difference
- Top line dominated
- Late goal decided it
- Shootout win
- Physical game with many penalties

### Notes

This uses existing data and adds a lot of flavor.

---

## P8.3 Season Milestones

### Examples

- Player reaches 50 goals.
- Player reaches 100 points.
- Goalie reaches 30 wins.
- Team clinches top seed.
- Team eliminated from contention.
- Rookie scores first goal.

---

# Priority 9 — Playoffs

Currently champion is based on regular-season standings. Playoffs would add drama.

---

## P9.1 Simple Playoff Bracket

### Goal

Add postseason.

### Possible Formats

For 30 teams:

    Top 8 qualify
    Best-of-7 series

Simpler/faster first version:

    Top 8 qualify
    Best-of-3 or best-of-5

### Notes

Best-of-3 or best-of-5 is better for early testing and faster seasons.

---

## P9.2 Playoff Stats

### Goal

Separate regular season and playoff stats.

### Tasks

- Mark games as regular season or playoff.
- Add playoff bracket UI.
- Add playoff player stats.
- Add champion screen.
- Preserve regular-season stats separately.

---

# Priority 10 — Advanced Simulation

These should remain parked unless the current sim feels insufficient.

---

## P10.1 Fatigue

### Goal

Make line usage and schedule density matter.

### Effects

- Ride top lines increases fatigue.
- Fatigue reduces performance.
- Roll all lines protects players.
- Back-to-back games matter.

### Notes

This would make gameplan choices more meaningful, but it creates another system that must be explained to the user.

---

## P10.2 Special Teams Units UI

### Goal

Let user configure PP and PK units.

### Features

- PP1
- PP2
- PK1
- PK2

### Notes

Requires more lineup UI and more validation. Do after basic roster management is stable.

---

## P10.3 Faceoffs

### Goal

Add center-specific value and possession starts.

### Requirements

- Faceoff rating
- Stoppage model
- Possession after goals/penalties/period starts

### Notes

Only useful if the sim becomes more play-by-play.

---

## P10.4 Zones / Full Play-by-Play

### Goal

Move toward a deeper hockey engine.

### Notes

High complexity. Keep far later.

---

# Priority 11 — User Experience / Quality

---

## P11.1 Better Onboarding

### Goal

Help new users understand the game.

### Topics to Explain

- Core loop
- OVR
- POT
- Development type
- Gameplan effects
- Lineup rules
- Standings
- Progression

### Possible UI

- First-run tutorial
- Tooltip cards
- Help drawer
- Glossary

---

## P11.2 Save/Load / Multi-Save

### Goal

Allow multiple leagues/saves.

### Features

- Continue save
- Create new save
- Rename save
- Delete save
- Save metadata

### Notes

Not needed until the game has enough replay value.

---

## P11.3 Auth

### Goal

Persistent hosted users.

### Notes

Only needed when deploying for real users.

Possible platform:

- Supabase Auth
- Supabase Postgres
- Supabase Storage

---

## P11.4 Mobile Layout

### Goal

Improve smaller-screen usability.

### Notes

Current project can remain desktop-first for now. Management games often work best on desktop/tablet.

---

# Priority 12 — Admin / Dev Tools

---

## P12.1 Season Analyzer

### Goal

Analyze real persisted seasons from the database.

### Location

Not inside `backend/sim`.

Suggested:

    backend/app/tools/analyze_season.py

or:

    backend/scripts/analyze_season.py

### Why

The pure sim package should remain DB-free. DB-backed diagnostic tools belong in app/tools or scripts.

### Metrics

- Top scorers
- OVR/attributes
- Team gameplan
- Line assignment
- Team GF/G
- Team SF/G
- L1/top3/top6 point share
- Shooting percentage
- Assists per goal
- PP contribution

---

## P12.2 Balance Test Suite

### Goal

Automated sample sims for tuning.

### Reports

- 1000-game scoring report
- Gameplan split report
- Development distribution report
- Injury rate report
- Free-agent strength distribution report
- Top-line concentration report

### Notes

Keep reports deterministic and broad. Avoid fragile exact-number assertions.

---

# Recommended Near-Term Roadmap

If the goal is to make the game more enjoyable as quickly as possible:

1. My Team + Player page clarity pass
2. Free agent pool
3. Sign/release players
4. Roster limits
5. Injuries
6. AI roster repair/free-agent signings
7. Contracts
8. Trades
9. Draft
10. Playoffs

---

# Current Best Next Milestone

## Roster Agency Phase

### Goal

The user can understand their roster, identify weaknesses, sign a better player, release a weak player, adjust lineup, and see the impact.

### Includes

- Player quality clarity
- Free agent pool
- Sign player
- Release player
- Roster limits
- Lineup validation after roster moves

### Out of Scope

- Salaries
- Contracts
- Trades
- Draft
- Salary cap
- Scouting fog
- AI bidding

### Why This Is Next

This is the missing management loop:

    Understand players → change roster → adjust lineup → sim → evaluate result

That will make the game feel much more like a management game.