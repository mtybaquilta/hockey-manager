from sqlalchemy.orm import Session

from app.models import Goalie, Lineup, Skater


def _by_pos(skaters: list[Skater], pos: str) -> list[Skater]:
    sk = [s for s in skaters if s.position == pos]
    sk.sort(key=lambda s: -(s.skating + s.shooting + s.passing + s.defense + s.physical))
    return sk


def generate_default_lineups(db: Session, team_ids: list[int]) -> None:
    for tid in team_ids:
        skaters = db.query(Skater).filter_by(team_id=tid).all()
        goalies = db.query(Goalie).filter_by(team_id=tid).all()
        goalies.sort(
            key=lambda g: -(g.reflexes + g.positioning + g.rebound_control + g.puck_handling + g.mental)
        )
        lws = _by_pos(skaters, "LW")
        cs = _by_pos(skaters, "C")
        rws = _by_pos(skaters, "RW")
        lds = _by_pos(skaters, "LD")
        rds = _by_pos(skaters, "RD")
        assert len(lws) >= 4 and len(cs) >= 4 and len(rws) >= 4
        assert len(lds) >= 3 and len(rds) >= 3
        assert len(goalies) >= 2
        lu = Lineup(
            team_id=tid,
            line1_lw_id=lws[0].id, line1_c_id=cs[0].id, line1_rw_id=rws[0].id,
            line2_lw_id=lws[1].id, line2_c_id=cs[1].id, line2_rw_id=rws[1].id,
            line3_lw_id=lws[2].id, line3_c_id=cs[2].id, line3_rw_id=rws[2].id,
            line4_lw_id=lws[3].id, line4_c_id=cs[3].id, line4_rw_id=rws[3].id,
            pair1_ld_id=lds[0].id, pair1_rd_id=rds[0].id,
            pair2_ld_id=lds[1].id, pair2_rd_id=rds[1].id,
            pair3_ld_id=lds[2].id, pair3_rd_id=rds[2].id,
            starting_goalie_id=goalies[0].id, backup_goalie_id=goalies[1].id,
        )
        db.add(lu)
    db.flush()
