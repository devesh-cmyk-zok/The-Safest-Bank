"""Every balance change goes through here. Callers own the commit.

Updates are conditional SQL statements (compare-and-set), so two requests racing on
the same held transfer can never both move its money.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from database.models import Transaction, TxStatus, User, utcnow


def _debit(db: Session, user_id: str, paise: int) -> bool:
    res = db.execute(
        update(User)
        .where(User.id == user_id, User.balance_paise >= paise)
        .values(balance_paise=User.balance_paise - paise)
    )
    return res.rowcount == 1


def _credit(db: Session, user_id: str, paise: int) -> None:
    db.execute(update(User).where(User.id == user_id).values(balance_paise=User.balance_paise + paise))


def _resolve(db: Session, tx: Transaction, to: TxStatus, by: str, note: str) -> bool:
    res = db.execute(
        update(Transaction)
        .where(Transaction.id == tx.id, Transaction.status == TxStatus.ESCROW_HELD)
        .values(status=to, resolved_at=utcnow(), resolved_by=by, resolution_note=note or None, otp_hash=None)
    )
    return res.rowcount == 1


def open_transfer(db: Session, tx: Transaction) -> bool:
    """Record a new transfer and move money for its status. False = insufficient funds."""
    if tx.status in (TxStatus.SETTLED, TxStatus.ESCROW_HELD):
        if not _debit(db, tx.user_id, tx.amount_paise):
            return False
        if tx.status == TxStatus.SETTLED:
            _credit(db, tx.recipient_id, tx.amount_paise)
    # AUTO_ABORTED: nothing moves, the row is the audit record.
    db.add(tx)
    return True


def settle_held(db: Session, tx: Transaction, by: str, note: str = "") -> bool:
    """Release held funds to the recipient. False if the transfer is no longer held."""
    if not _resolve(db, tx, TxStatus.SETTLED, by, note):
        return False
    _credit(db, tx.recipient_id, tx.amount_paise)
    return True


def refund_held(db: Session, tx: Transaction, to: TxStatus, by: str, note: str = "") -> bool:
    """Return held funds to the sender (customer cancel or SOC block)."""
    if not _resolve(db, tx, to, by, note):
        return False
    _credit(db, tx.user_id, tx.amount_paise)
    return True
