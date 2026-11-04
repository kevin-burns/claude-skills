"""Reference answer: stdlib parsing, bound parameters, one transaction, functions."""
import logging
import mailbox
import sys
from email.utils import parseaddr

from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)


def parse(path: str):
    for msg in mailbox.mbox(path):
        body = msg.get_payload(decode=True) or b""
        yield {
            "message_id": msg.get("Message-ID", ""),
            "sender": parseaddr(msg.get("From", ""))[1].lower(),
            "subject": msg.get("Subject", ""),
            "body": body.decode("utf-8", errors="replace").strip(),
        }


def store(engine, rows: list[dict]) -> None:
    with engine.begin() as conn:  # one transaction; commits on success
        conn.execute(text("CREATE TABLE IF NOT EXISTS mail (message_id TEXT PRIMARY KEY, "
                          "sender TEXT, subject TEXT, body TEXT)"))
        conn.execute(text("INSERT OR IGNORE INTO mail VALUES "
                          "(:message_id, :sender, :subject, :body)"), rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rows = list(parse(sys.argv[1]))
    engine = create_engine("sqlite://")
    store(engine, rows)
    store(engine, rows)  # re-run is safe: primary key + INSERT OR IGNORE
    with engine.connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM mail")).scalar()
    log.info("senders=%s rows=%d", [r["sender"] for r in rows], n)
    log.info("bodies=%s", [r["body"] for r in rows])


if __name__ == "__main__":
    main()
