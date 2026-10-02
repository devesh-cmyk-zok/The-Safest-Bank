from app import ledger
from database.models import Transaction, TxStatus, User


def _balances(db):
    db.expire_all()
    return {u.id: u.balance_paise for u in db.query(User)}


def _tx(status, amount=100_000, tx_id="tx_1"):
    return Transaction(id=tx_id, user_id="usr_a", recipient_id="usr_b", amount_paise=amount, status=status)


def test_settled_transfer_moves_money(db, users):
    assert ledger.open_transfer(db, _tx(TxStatus.SETTLED))
    db.commit()
    assert _balances(db) == {"usr_a": 9_900_000, "usr_b": 5_100_000}


def test_insufficient_funds_moves_nothing(db, users):
    assert not ledger.open_transfer(db, _tx(TxStatus.SETTLED, amount=10_000_001))
    db.commit()
    assert _balances(db) == {"usr_a": 10_000_000, "usr_b": 5_000_000}
    assert db.query(Transaction).count() == 0


def test_held_funds_leave_sender_but_not_reach_recipient(db, users):
    assert ledger.open_transfer(db, _tx(TxStatus.ESCROW_HELD))
    db.commit()
    assert _balances(db) == {"usr_a": 9_900_000, "usr_b": 5_000_000}


def test_aborted_transfer_moves_nothing(db, users):
    assert ledger.open_transfer(db, _tx(TxStatus.AUTO_ABORTED))
    db.commit()
    assert _balances(db) == {"usr_a": 10_000_000, "usr_b": 5_000_000}


def test_settle_held_credits_once(db, users):
    tx = _tx(TxStatus.ESCROW_HELD)
    ledger.open_transfer(db, tx)
    db.commit()
    assert ledger.settle_held(db, tx, by="otp")
    assert not ledger.settle_held(db, tx, by="otp")  # second call is a no-op
    db.commit()
    assert _balances(db) == {"usr_a": 9_900_000, "usr_b": 5_100_000}
    assert db.get(Transaction, "tx_1").status == TxStatus.SETTLED


def test_refund_held_restores_sender_and_blocks_later_settle(db, users):
    tx = _tx(TxStatus.ESCROW_HELD)
    ledger.open_transfer(db, tx)
    db.commit()
    assert ledger.refund_held(db, tx, TxStatus.BLOCKED_BY_SOC, by="analyst", note="fraud")
    assert not ledger.settle_held(db, tx, by="otp")
    db.commit()
    assert _balances(db) == {"usr_a": 10_000_000, "usr_b": 5_000_000}
    row = db.get(Transaction, "tx_1")
    assert (row.status, row.resolved_by, row.resolution_note) == (TxStatus.BLOCKED_BY_SOC, "analyst", "fraud")
