import time

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///:memory:")
with engine.connect() as conn:
    conn.execute(text("CREATE TABLE t (n INTEGER)"))
    conn.commit()
    start = time.perf_counter()
    for n in range(2000):
        conn.execute(text("INSERT INTO t VALUES (:n)"), {"n": n})
        conn.commit()
    per_row = time.perf_counter() - start
    start = time.perf_counter()
    conn.execute(text("INSERT INTO t VALUES (:n)"), [{"n": n} for n in range(2000)])
    conn.commit()
    bulk = time.perf_counter() - start
    print(conn.execute(text("SELECT count(*) FROM t")).scalar(), per_row > bulk)
