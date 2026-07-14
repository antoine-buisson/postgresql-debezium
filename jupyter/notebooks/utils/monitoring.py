import logging
import traceback
from datetime import datetime, timezone

import psycopg2
from pyspark.sql.streaming import StreamingQueryListener

logger = logging.getLogger("streaming_heartbeat")

class PostgresHeartbeatListener(StreamingQueryListener):
    def __init__(self, dsn):
        self.dsn = dsn
        self._ensure_ready()

    def _get_conn(self):
        # simple per-call connection; fine at heartbeat frequency (secs-scale)
        return psycopg2.connect(self.dsn)
    
    def _ensure_ready(self):
        sql = """
        CREATE TABLE IF NOT EXISTS streaming_query_heartbeat (
            query_name      TEXT,
            query_id        TEXT PRIMARY KEY,
            run_id          TEXT NOT NULL,
            status          TEXT NOT NULL,          -- STARTED, RUNNING, TERMINATED
            last_batch_id   BIGINT,
            input_rows_per_sec   DOUBLE PRECISION,
            processed_rows_per_sec DOUBLE PRECISION,
            batch_duration_ms    BIGINT,
            error_message   TEXT,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def _upsert(self, query_id, run_id, status, query_name=None,
        last_batch_id=None, input_rate=None, proc_rate=None,
        batch_duration=None, error=None):
        try:
            sql = """
            INSERT INTO streaming_query_heartbeat
                (query_name, query_id, run_id, status, last_batch_id,
                input_rows_per_sec, processed_rows_per_sec, batch_duration_ms,
                error_message, updated_at)
            VALUES (COALESCE(%(query_name)s, %(query_id)s), %(query_id)s, %(run_id)s,
                    %(status)s, %(last_batch_id)s, %(input_rate)s, %(proc_rate)s,
                    %(batch_duration)s, %(error)s, now())
            ON CONFLICT (query_id) DO UPDATE SET
                query_name = COALESCE(EXCLUDED.query_name, streaming_query_heartbeat.query_name),
                run_id = EXCLUDED.run_id,
                status = EXCLUDED.status,
                last_batch_id = EXCLUDED.last_batch_id,
                input_rows_per_sec = EXCLUDED.input_rows_per_sec,
                processed_rows_per_sec = EXCLUDED.processed_rows_per_sec,
                batch_duration_ms = EXCLUDED.batch_duration_ms,
                error_message = EXCLUDED.error_message,
                updated_at = now();
            """
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, {
                        "query_name": query_name,
                        "query_id": query_id,
                        "run_id": run_id,
                        "status": status,
                        "last_batch_id": last_batch_id,
                        "input_rate": input_rate,
                        "proc_rate": proc_rate,
                        "batch_duration": batch_duration,
                        "error": error,
                    })
        except Exception:
            logger.error("Heartbeat upsert failed:\n%s", traceback.format_exc())

    def onQueryStarted(self, event):
        self._upsert(
            query_name=event.name,
            query_id=str(event.id),
            run_id=str(event.runId),
            status="STARTED",
        )

    def onQueryProgress(self, event):
        p = event.progress
        # p.durationMs is a dict like {"triggerExecution": 1234, ...}
        duration = p.durationMs.get("triggerExecution") if p.durationMs else None
        self._upsert(
            query_name=p.name,
            query_id=str(p.id),
            run_id=str(p.runId),
            status="RUNNING",
            last_batch_id=p.batchId,
            input_rate=p.inputRowsPerSecond,
            proc_rate=p.processedRowsPerSecond,
            batch_duration=duration,
        )

    def onQueryTerminated(self, event):
        err = str(event.exception) if event.exception else None
        self._upsert(
            query_id=str(event.id),
            run_id=str(event.runId),
            status="TERMINATED",
            error=err,
        )
        
    def printStatus(self):
        sql = """
            SELECT query_name, status, last_batch_id,
                input_rows_per_sec, processed_rows_per_sec,
                batch_duration_ms, updated_at, error_message
            FROM streaming_query_heartbeat
            ORDER BY query_name;
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    colnames = [desc[0] for desc in cur.description]
        except Exception:
            logger.error("Failed to fetch heartbeat status:\n%s", traceback.format_exc())
            return

        if not rows:
            print("No streaming queries registered yet.")
            return

        now = datetime.now(timezone.utc)
        headers = ["query", "status", "batch", "in/s", "proc/s", "dur(ms)", "age", "error"]
        widths = [18, 11, 7, 8, 8, 8, 8, 30]

        def fmt_row(vals):
            return "  ".join(str(v).ljust(w)[:w] for v, w in zip(vals, widths))

        print(fmt_row(headers))
        print("  ".join("-" * w for w in widths))

        for name, status, batch_id, in_rate, proc_rate, dur_ms, updated_at, error in rows:
            age_s = (now - updated_at).total_seconds()
            age_str = f"{age_s:.0f}s"

            # flag stale rows so you can spot dead/stuck queries at a glance
            stale = age_s > 60
            status_display = f"{status}{'  ⚠ STALE' if stale else ''}"

            row = [
                name or "-",
                status_display,
                batch_id if batch_id is not None else "-",
                f"{in_rate:.1f}" if in_rate is not None else "-",
                f"{proc_rate:.1f}" if proc_rate is not None else "-",
                dur_ms if dur_ms is not None else "-",
                age_str,
                (error[:27] + "...") if error and len(error) > 30 else (error or "-"),
            ]
            print(fmt_row(row))