"""
sle.exporters — 导出器模块
===========================
提供 CSV / JSON / SQLite 三种格式的导出器。

每个导出器实现 export(rows, output, selected_columns) 接口。
工厂函数 get_exporter(fmt) 返回对应实例。
"""

import csv
import json
import sqlite3

from sle.engine import CN_COLUMNS, ALL_COLUMNS


# ── 列类型推断（用于 SQLite） ────────────────────────────────────────

INTEGER_COLUMNS = {"appid", "metacritic_score", "total_positive",
                   "total_negative", "total_reviews"}
REAL_COLUMNS = {"playtime_hours", "playtime_2weeks_hours",
                "avg_playtime_global", "median_playtime_global"}


def _sqlite_type(col: str) -> str:
    if col in INTEGER_COLUMNS:
        return "INTEGER"
    if col in REAL_COLUMNS:
        return "REAL"
    return "TEXT"


def _sqlite_value(col: str, val) -> object:
    if val == "" or val is None:
        return None
    if col in INTEGER_COLUMNS:
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
    if col in REAL_COLUMNS:
        try:
            return float(val)
        except (ValueError, TypeError):
            return val
    return str(val)


# ── 导出器基类 ────────────────────────────────────────────────────────

class BaseExporter:
    def export(self, rows: list[dict], output: str,
               selected_columns: set | None = None):
        raise NotImplementedError

    @staticmethod
    def _resolve_columns(rows, selected_columns):
        """返回要导出的英文字段名列表，过滤内部排序字段。"""
        if selected_columns:
            return [k for k in ALL_COLUMNS if k in selected_columns]
        return [k for k in ALL_COLUMNS if k in rows[0]]


# ── CSV 导出器 ────────────────────────────────────────────────────────

class CSVExporter(BaseExporter):
    def export(self, rows, output, selected_columns=None):
        if not rows:
            return
        en_fieldnames = self._resolve_columns(rows, selected_columns)

        cn_fieldnames = [CN_COLUMNS.get(k, k) for k in en_fieldnames]
        cn_rows = [
            {CN_COLUMNS.get(k, k): row.get(k, "") for k in en_fieldnames}
            for row in rows
        ]
        with open(output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=cn_fieldnames)
            writer.writeheader()
            writer.writerows(cn_rows)


# ── JSON 导出器 ───────────────────────────────────────────────────────

class JSONExporter(BaseExporter):
    def export(self, rows, output, selected_columns=None):
        if not rows:
            return
        en_fieldnames = self._resolve_columns(rows, selected_columns)

        json_rows = [{k: row.get(k, "") for k in en_fieldnames} for row in rows]
        with open(output, "w", encoding="utf-8") as f:
            json.dump(json_rows, f, indent=2, ensure_ascii=False)


# ── SQLite 导出器 ─────────────────────────────────────────────────────

class SQLiteExporter(BaseExporter):
    def export(self, rows, output, selected_columns=None):
        if not rows:
            return
        en_fieldnames = self._resolve_columns(rows, selected_columns)

        conn = sqlite3.connect(output)
        try:
            conn.execute("DROP TABLE IF EXISTS steam_library")

            col_defs = []
            for col in en_fieldnames:
                col_defs.append(f'"{col}" {_sqlite_type(col)}')
            create_sql = f"CREATE TABLE steam_library ({', '.join(col_defs)})"
            conn.execute(create_sql)

            placeholders = ", ".join("?" for _ in en_fieldnames)
            quoted_cols = [f'"{c}"' for c in en_fieldnames]
            insert_sql = f"INSERT INTO steam_library ({', '.join(quoted_cols)}) VALUES ({placeholders})"

            for row in rows:
                values = [_sqlite_value(col, row.get(col, "")) for col in en_fieldnames]
                conn.execute(insert_sql, values)

            conn.commit()
        finally:
            conn.close()


# ── 工厂函数 ──────────────────────────────────────────────────────────

_EXPORTERS = {
    "csv": CSVExporter,
    "json": JSONExporter,
    "sqlite": SQLiteExporter,
}


def get_exporter(fmt: str) -> BaseExporter:
    if fmt not in _EXPORTERS:
        raise ValueError(f"不支持的格式: {fmt}，可选: {list(_EXPORTERS.keys())}")
    return _EXPORTERS[fmt]()
