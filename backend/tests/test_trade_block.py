from app.models import Goalie, Skater, Team
from app.services.league_service import create_or_reset_league
from app.services.trade_service import compute_trade_block


def _setup(db, seed=42):
    season = create_or_reset_league(db, seed=seed)
    db.flush()
    return season


def test_block_excludes_user_team(db):
    season = _setup(db)
    block = compute_trade_block(db)
    assert block, "expected at least one trade-block entry across AI teams"
    assert all(e["team_id"] != season.user_team_id for e in block)


def test_block_returns_at_most_3_per_team(db):
    _setup(db)
    block = compute_trade_block(db)
    counts: dict[int, int] = {}
    for e in block:
        counts[e["team_id"]] = counts.get(e["team_id"], 0) + 1
    assert counts, "expected entries"
    assert all(c <= 3 for c in counts.values())


def test_block_excludes_top_core_per_ai_team(db):
    _setup(db)
    block = compute_trade_block(db)
    # For each AI team, recompute top-3 F + top-2 D + top-1 G; none should appear in block.
    teams = db.query(Team).all()
    block_ids = {(e["player_type"], e["player_id"]) for e in block}
    for team in teams:
        skaters = db.query(Skater).filter(Skater.team_id == team.id).all()
        goalies = db.query(Goalie).filter(Goalie.team_id == team.id).all()
        if not skaters and not goalies:
            continue

        def _sk_ovr(s):
            return (s.skating + s.shooting + s.passing + s.defense + s.physical) / 5

        def _g_ovr(g):
            return (g.reflexes + g.positioning + g.rebound_control + g.puck_handling + g.mental) / 5

        fwd = sorted([s for s in skaters if s.position not in ("LD", "RD")], key=lambda s: -_sk_ovr(s))
        df = sorted([s for s in skaters if s.position in ("LD", "RD")], key=lambda s: -_sk_ovr(s))
        gs = sorted(goalies, key=lambda x: -_g_ovr(x))
        for s in fwd[:3]:
            assert ("skater", s.id) not in block_ids
        for s in df[:2]:
            assert ("skater", s.id) not in block_ids
        for g in gs[:1]:
            assert ("goalie", g.id) not in block_ids


def test_block_is_deterministic(db):
    _setup(db)
    a = compute_trade_block(db)
    b = compute_trade_block(db)
    assert a == b


def test_block_entry_shape(db):
    _setup(db)
    block = compute_trade_block(db)
    e = block[0]
    assert set(e.keys()) >= {
        "player_type", "player_id", "team_id", "team_name", "team_abbreviation",
        "name", "age", "position", "ovr", "asking_value", "reason",
    }
    assert e["player_type"] in ("skater", "goalie")
    if e["player_type"] == "skater":
        assert e["position"] is not None
    else:
        assert e["position"] is None
    assert isinstance(e["ovr"], int)
    assert isinstance(e["asking_value"], int)
