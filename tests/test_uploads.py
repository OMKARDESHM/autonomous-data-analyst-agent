import io
import os
import pandas as pd
from uploads import create_engine_from_uploaded
from sqlalchemy import text


class DummyUpload:
    def __init__(self, content: bytes, name: str):
        self._b = content
        self.name = name

    def getbuffer(self):
        return self._b


def test_create_engine_from_csv(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    up = DummyUpload(csv_bytes, "test.csv")
    engine, path = create_engine_from_uploaded(up, up.name)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM test"))
        assert res.scalar() == 3
    os.remove(path)


def test_create_engine_from_parquet(tmp_path):
    df = pd.DataFrame({"a": [10, 20], "b": ["p", "q"]})
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    parquet_bytes = buf.getvalue()
    up = DummyUpload(parquet_bytes, "data.parquet")
    engine, path = create_engine_from_uploaded(up, up.name)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM data"))
        assert res.scalar() == 2
    os.remove(path)
