from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Contract


class ContractStateError(DomainError):
    code = "ContractStateError"
    status = 409


def get_active_contract_for_skater(db: Session, skater_id: int) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.skater_id == skater_id, Contract.status == "active")
        .one_or_none()
    )


def get_active_contract_for_goalie(db: Session, goalie_id: int) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.goalie_id == goalie_id, Contract.status == "active")
        .one_or_none()
    )


def create_contract_for_skater(
    db: Session,
    skater_id: int,
    *,
    length: int,
    signed_season_year: int,
    salary: int,
    no_trade_clause: bool = False,
) -> Contract:
    c = Contract(
        skater_id=skater_id,
        length=length,
        signed_season_year=signed_season_year,
        expires_after_year=signed_season_year + length - 1,
        salary=salary,
        no_trade_clause=no_trade_clause,
        status="active",
    )
    db.add(c)
    db.flush()
    return c


def create_contract_for_goalie(
    db: Session,
    goalie_id: int,
    *,
    length: int,
    signed_season_year: int,
    salary: int,
    no_trade_clause: bool = False,
) -> Contract:
    c = Contract(
        goalie_id=goalie_id,
        length=length,
        signed_season_year=signed_season_year,
        expires_after_year=signed_season_year + length - 1,
        salary=salary,
        no_trade_clause=no_trade_clause,
        status="active",
    )
    db.add(c)
    db.flush()
    return c


def terminate_contract(db: Session, contract: Contract, *, season_year: int) -> None:
    if contract.status != "active":
        raise ContractStateError(
            f"contract {contract.id} status={contract.status!r}; cannot terminate"
        )
    contract.status = "terminated"
    contract.terminated_season_year = season_year
    db.flush()


def expire_contracts_through_year(
    db: Session, *, new_season_year: int
) -> list[tuple[str, int]]:
    """Flip every active contract whose expires_after_year < new_season_year
    to status='expired'. Returns a list of (player_type, player_id) for the
    affected players so callers can null team_id and clear lineup slots."""
    rows = (
        db.query(Contract)
        .filter(
            Contract.status == "active",
            Contract.expires_after_year < new_season_year,
        )
        .all()
    )
    out: list[tuple[str, int]] = []
    for c in rows:
        c.status = "expired"
        if c.skater_id is not None:
            out.append(("skater", c.skater_id))
        else:
            assert c.goalie_id is not None
            out.append(("goalie", c.goalie_id))
    db.flush()
    return out


def years_remaining(contract: Contract, *, season_year: int) -> int:
    return max(0, contract.expires_after_year - season_year + 1)
