"""
sle.gui — Steam Library Exporter GUI components
================================================
tkinter-based GUI for the export engine.

Provides:
  - I18n: internationalization manager
  - EnvManager: .env file read/write
  - SettingsDialog: credentials + theme/language settings
  - ColumnSelectDialog: grouped column selection
  - SteamExportGUI: main application window
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

import tomllib

from sle.engine import (
    run_export, ALL_COLUMNS, CN_COLUMNS, GROUP_FIELDS,
)

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
I18N_PATH = CONFIG_DIR / "i18n.toml"
ENV_PATH = CONFIG_DIR / ".env"
SETTINGS_PATH = CONFIG_DIR / "settings.toml"


# ── I18n Manager ──────────────────────────────────────────────────────

class I18n:
    def __init__(self, lang: str = "zh"):
        with open(I18N_PATH, "rb") as f:
            self._data = tomllib.load(f)
        self._lang = lang
        self._gui = self._data.get("gui", {})
        self._col_groups = self._data.get("col_groups", {})

    @property
    def lang(self) -> str:
        return self._lang

    @lang.setter
    def lang(self, value: str):
        self._lang = value

    def t(self, key: str) -> str:
        lang_data = self._gui.get(self._lang, {})
        return lang_data.get(key, key)

    def column_name(self, en_key: str) -> str:
        return CN_COLUMNS.get(en_key, en_key)

    def group_label(self, group_key: str) -> str:
        g = self._col_groups.get(group_key, {})
        label_key = f"label_{self._lang}"
        return g.get(label_key, g.get("label_zh", group_key))

    def group_desc(self, group_key: str) -> str:
        g = self._col_groups.get(group_key, {})
        desc_key = f"desc_{self._lang}"
        return g.get(desc_key, g.get("desc_zh", ""))

    def group_delay(self, group_key: str) -> float:
        g = self._col_groups.get(group_key, {})
        return g.get("per_game_delay", 0.0)


# ── Env Manager ───────────────────────────────────────────────────────

def _load_settings_defaults() -> dict:
    """Load defaults from config/settings.toml if it exists."""
    defaults = {
        "STEAM_API_KEY": "",
        "STEAM_ID": "",
        "THEME": "clam",
        "LANGUAGE": "zh",
        "SELECTED_COLUMNS": ",".join(ALL_COLUMNS),
    }
    if not SETTINGS_PATH.exists():
        return defaults
    try:
        with open(SETTINGS_PATH, "rb") as f:
            data = tomllib.load(f)
        d = data.get("defaults", {})
        for k in defaults:
            if k in d:
                defaults[k] = d[k] if not isinstance(d[k], bool) else str(d[k])
    except Exception:
        pass
    return defaults


class EnvManager:
    DEFAULTS = _load_settings_defaults()

    @staticmethod
    def load() -> dict:
        result = dict(EnvManager.DEFAULTS)
        if not ENV_PATH.exists():
            return result
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip()
        return result

    @staticmethod
    def save(data: dict):
        lines = []
        for key, value in data.items():
            lines.append(f"{key}={value}")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ── Settings Dialog ───────────────────────────────────────────────────

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, i18n: I18n, env_data: dict):
        super().__init__(parent)
        self.i18n = i18n
        self.env_data = env_data

        self.title(i18n.t("settings_title"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._apply_language()
        self._center_on_parent(parent)

    def _build_ui(self):
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._tab_cred = ttk.Frame(self._notebook)
        self._notebook.add(self._tab_cred, text="Credentials")
        self._tab_cred._i18n_key = "tab_credentials"

        frm = ttk.Frame(self._tab_cred, padding=15)
        frm.pack(fill="both", expand=True)

        self._lbl_key = ttk.Label(frm, text="API Key:")
        self._lbl_key._i18n_key = "label_api_key"
        self._entry_key = ttk.Entry(frm, width=45, show="*")
        self._entry_key.insert(0, self.env_data.get("STEAM_API_KEY", ""))
        self._entry_key.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self._show_key_var = tk.BooleanVar()
        self._chk_show_key = ttk.Checkbutton(
            frm, text="Show", variable=self._show_key_var,
            command=self._toggle_key_visibility,
        )
        self._chk_show_key.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(0, 10))

        self._lbl_sid = ttk.Label(frm, text="Steam64 ID:")
        self._lbl_sid._i18n_key = "label_steam_id"
        self._entry_sid = ttk.Entry(frm, width=45)
        self._entry_sid.insert(0, self.env_data.get("STEAM_ID", ""))
        self._entry_sid.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self._tab_app = ttk.Frame(self._notebook)
        self._notebook.add(self._tab_app, text="Appearance")
        self._tab_app._i18n_key = "tab_appearance"

        frm2 = ttk.Frame(self._tab_app, padding=15)
        frm2.pack(fill="both", expand=True)

        self._lbl_theme = ttk.Label(frm2, text="Theme:")
        self._lbl_theme._i18n_key = "label_theme"
        self._lbl_theme.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self._theme_var = tk.StringVar(value=self.env_data.get("THEME", "clam"))
        themes = sorted(ttk.Style().theme_names())
        self._combo_theme = ttk.Combobox(
            frm2, textvariable=self._theme_var, values=themes,
            state="readonly", width=25,
        )
        self._combo_theme.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self._combo_theme.bind("<<ComboboxSelected>>", self._on_theme_change)

        self._lbl_lang = ttk.Label(frm2, text="Language:")
        self._lbl_lang._i18n_key = "label_language"
        self._lbl_lang.grid(row=2, column=0, sticky="w", pady=(0, 5))
        self._lang_var = tk.StringVar(value=self.env_data.get("LANGUAGE", "zh"))
        self._combo_lang = ttk.Combobox(
            frm2, textvariable=self._lang_var,
            values=["zh", "en"], state="readonly", width=25,
        )
        self._combo_lang.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        self._combo_lang.bind("<<ComboboxSelected>>", self._on_lang_change)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._btn_save = ttk.Button(btn_frame, text="Save", command=self._on_save)
        self._btn_save._i18n_key = "save_btn_settings"
        self._btn_save.pack(side="right", padx=(5, 0))
        self._btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self._btn_cancel._i18n_key = "cancel_btn_settings"
        self._btn_cancel.pack(side="right")

    def _toggle_key_visibility(self):
        show = self._show_key_var.get()
        self._entry_key.configure(show="" if show else "*")

    def _on_theme_change(self, event=None):
        theme = self._theme_var.get()
        ttk.Style().theme_use(theme)
        self.env_data["THEME"] = theme

    def _on_lang_change(self, event=None):
        lang = self._lang_var.get()
        self.env_data["LANGUAGE"] = lang
        self.i18n.lang = lang
        self._apply_language()
        self.master._apply_language()

    def _on_save(self):
        self.env_data["STEAM_API_KEY"] = self._entry_key.get()
        self.env_data["STEAM_ID"] = self._entry_sid.get()
        EnvManager.save(self.env_data)
        self.destroy()
        self.master._load_env()

    def _apply_language(self):
        i = self.i18n
        self.title(i.t("settings_title"))
        for widget in self._all_widgets():
            key = getattr(widget, "_i18n_key", None)
            if key:
                try:
                    widget.configure(text=i.t(key))
                except tk.TclError:
                    pass
        self._notebook.tab(self._tab_cred, text=i.t("tab_credentials"))
        self._notebook.tab(self._tab_app, text=i.t("tab_appearance"))
        self._lbl_key.configure(text=i.t("label_api_key") + ":")
        self._lbl_sid.configure(text=i.t("label_steam_id") + ":")
        self._lbl_theme.configure(text=i.t("label_theme") + ":")
        self._lbl_lang.configure(text=i.t("label_language") + ":")
        self._btn_save.configure(text=i.t("save_btn_settings"))
        self._btn_cancel.configure(text=i.t("cancel_btn_settings"))

    def _all_widgets(self):
        result = []
        self._walk_widgets(self, result)
        return result

    def _walk_widgets(self, widget, result):
        result.append(widget)
        for child in widget.winfo_children():
            self._walk_widgets(child, result)

    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")


# ── Column Select Dialog ──────────────────────────────────────────────

class ColumnSelectDialog(tk.Toplevel):
    def __init__(self, parent, i18n: I18n, selected: set):
        super().__init__(parent)
        self.i18n = i18n
        self.selected = set(selected)
        self._group_vars: dict[str, tk.BooleanVar] = {}
        self._item_vars: dict[str, tk.BooleanVar] = {}
        self._result = None

        self.title(i18n.t("col_select_title"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._apply_language()
        self._center_on_parent(parent)

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        group_keys = ["core", "store", "reviews", "steamspy"]
        for gk in group_keys:
            fields = GROUP_FIELDS.get(gk, [])
            if not fields:
                continue

            gf = ttk.LabelFrame(main_frame, text=gk, padding=5)
            gf._i18n_group = gk
            gf.pack(fill="x", pady=(0, 8))

            group_var = tk.BooleanVar(value=all(f in self.selected for f in fields))
            self._group_vars[gk] = group_var
            gc = ttk.Checkbutton(
                gf, text="", variable=group_var,
                command=lambda g=gk: self._toggle_group(g),
            )
            gc._i18n_group_cb = gk
            gc.pack(anchor="w", padx=5)

            inner = ttk.Frame(gf, padding=5)
            inner.pack(fill="x")

            for idx, field in enumerate(fields):
                cn_name = self.i18n.column_name(field)
                var = tk.BooleanVar(value=field in self.selected)
                self._item_vars[field] = var
                cb = ttk.Checkbutton(
                    inner, text=cn_name, variable=var,
                    command=lambda f=field, gk=gk: self._on_item_toggle(f, gk),
                )
                row = idx // 2
                col = idx % 2
                cb.grid(row=row, column=col, sticky="w", padx=2, pady=1)

        bottom = ttk.Frame(main_frame, padding=(0, 5, 0, 0))
        bottom.pack(fill="x")

        self._btn_all = ttk.Button(bottom, text="Select All", command=self._select_all)
        self._btn_all._i18n_key = "btn_select_all"
        self._btn_all.pack(side="left", padx=(0, 5))
        self._btn_none = ttk.Button(bottom, text="Deselect All", command=self._deselect_all)
        self._btn_none._i18n_key = "btn_deselect_all"
        self._btn_none.pack(side="left")

        self._lbl_count = ttk.Label(bottom, text="")
        self._lbl_count._i18n_key = "label_total_selected"
        self._lbl_count.pack(side="right")

        btn_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        btn_frame.pack(fill="x")
        self._btn_ok = ttk.Button(btn_frame, text="OK", command=self._on_ok)
        self._btn_ok._i18n_key = "col_select_confirm"
        self._btn_ok.pack(side="right", padx=(5, 0))
        self._btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self._btn_cancel._i18n_key = "col_select_cancel"
        self._btn_cancel.pack(side="right")

        self._update_count()

    def _toggle_group(self, group_key: str):
        all_on = self._group_vars[group_key].get()
        for field in GROUP_FIELDS.get(group_key, []):
            self._item_vars[field].set(all_on)
            if all_on:
                self.selected.add(field)
            else:
                self.selected.discard(field)
        self._update_count()

    def _on_item_toggle(self, field: str, group_key: str):
        if self._item_vars[field].get():
            self.selected.add(field)
        else:
            self.selected.discard(field)
        fields = GROUP_FIELDS.get(group_key, [])
        all_on = all(self._item_vars[f].get() for f in fields)
        self._group_vars[group_key].set(all_on)
        self._update_count()

    def _select_all(self):
        for field in ALL_COLUMNS:
            self.selected.add(field)
            if field in self._item_vars:
                self._item_vars[field].set(True)
        for v in self._group_vars.values():
            v.set(True)
        self._update_count()

    def _deselect_all(self):
        self.selected.clear()
        for v in self._item_vars.values():
            v.set(False)
        for v in self._group_vars.values():
            v.set(False)
        self._update_count()

    def _on_ok(self):
        self._result = set(self.selected)
        self.destroy()

    @property
    def result(self):
        return self._result

    def _update_count(self):
        i = self.i18n
        count = len(self.selected)
        total = len(ALL_COLUMNS)
        tmpl = i.t("label_total_selected")
        if "{}/{}" in tmpl:
            text = tmpl.replace("{}/{}", f"{count}/{total}")
        elif "{}" in tmpl:
            text = tmpl.replace("{}", f"{count}/{total}")
        else:
            text = f"{tmpl} {count}/{total}"
        self._lbl_count.configure(text=text)

        delay = 0.0
        for gk, gd in GROUP_FIELDS.items():
            if any(self._item_vars.get(f) and self._item_vars[f].get() for f in gd):
                delay += self.i18n.group_delay(gk)
        sec_per_game = delay + 0.3
        if sec_per_game < 60:
            per_str = f"~{sec_per_game:.0f}s"
        elif sec_per_game < 3600:
            per_str = f"~{sec_per_game / 60:.0f}min"
        else:
            per_str = f"~{sec_per_game / 3600:.1f}h"
        self._lbl_count.configure(
            text=f"{text}     {i.t('label_est_time')}: {per_str}/game"
        )

    def _apply_language(self):
        i = self.i18n
        self.title(i.t("col_select_title"))
        self._btn_all.configure(text=i.t("btn_select_all"))
        self._btn_none.configure(text=i.t("btn_deselect_all"))
        self._btn_ok.configure(text=i.t("col_select_confirm"))
        self._btn_cancel.configure(text=i.t("col_select_cancel"))
        for widget in self.winfo_children():
            self._apply_lang_widget(widget, i)
        self._update_count()

    def _apply_lang_widget(self, widget, i):
        if isinstance(widget, ttk.LabelFrame):
            gk = getattr(widget, "_i18n_group", None)
            if gk:
                label = i.group_label(gk)
                desc = i.group_desc(gk)
                widget.configure(text=f"  {label}  ({desc})  ")
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton):
                    gk2 = getattr(child, "_i18n_group_cb", None)
                    if gk2:
                        child.configure(text=i.group_label(gk2))
        if isinstance(widget, ttk.Checkbutton):
            for field, var in self._item_vars.items():
                if widget.cget("variable") == str(var):
                    widget.configure(text=i.column_name(field))
                    break
        for child in widget.winfo_children():
            self._apply_lang_widget(child, i)

    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")


# ── Main Window ───────────────────────────────────────────────────────

class SteamExportGUI:
    def __init__(self):
        self.env_data = EnvManager.load()
        lang = self.env_data.get("LANGUAGE", "zh")
        self.i18n = I18n(lang)

        sel_str = self.env_data.get("SELECTED_COLUMNS", "")
        if sel_str:
            self.selected_columns = set(
                c.strip() for c in sel_str.split(",") if c.strip() in ALL_COLUMNS
            )
        else:
            self.selected_columns = set(ALL_COLUMNS)

        self._cancel_event = threading.Event()
        self._export_thread = None
        self._export_running = False

        self.root = tk.Tk()
        self._build_ui()
        self._apply_language()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _build_ui(self):
        self.root.title(self.i18n.t("window_title"))
        self.root.geometry("780x650")
        self.root.minsize(650, 500)

        theme = self.env_data.get("THEME", "clam")
        available = ttk.Style().theme_names()
        if theme in available:
            ttk.Style().theme_use(theme)

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # ── Credentials ──
        cred_frame = ttk.LabelFrame(main, text="Credentials", padding=8)
        cred_frame._i18n_key = "section_credentials"
        cred_frame.pack(fill="x", pady=(0, 8))

        cred_inner = ttk.Frame(cred_frame)
        cred_inner.pack(fill="x")

        self._lbl_key = ttk.Label(cred_inner, text="API Key:")
        self._lbl_key._i18n_key = "label_api_key"
        self._lbl_key.grid(row=0, column=0, sticky="e", padx=(0, 5))
        self._entry_key = ttk.Entry(cred_inner, width=40, show="*", state="readonly")
        self._entry_key.grid(row=0, column=1, sticky="ew")

        self._lbl_sid = ttk.Label(cred_inner, text="Steam64 ID:")
        self._lbl_sid._i18n_key = "label_steam_id"
        self._lbl_sid.grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(4, 0))
        self._entry_sid = ttk.Entry(cred_inner, width=40, state="readonly")
        self._entry_sid.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        self._btn_settings = ttk.Button(
            cred_inner, text="Settings", command=self._open_settings,
        )
        self._btn_settings._i18n_key = "btn_settings"
        self._btn_settings.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="ns")

        cred_inner.columnconfigure(1, weight=1)

        # ── Export options ──
        export_frame = ttk.LabelFrame(main, text="Export Options", padding=8)
        export_frame._i18n_key = "section_export"
        export_frame.pack(fill="x", pady=(0, 8))

        exp = ttk.Frame(export_frame)
        exp.pack(fill="x")

        self._lbl_output = ttk.Label(exp, text="Output:")
        self._lbl_output._i18n_key = "label_output"
        self._lbl_output.grid(row=0, column=0, sticky="e", padx=(0, 5))
        self._entry_output = ttk.Entry(exp, width=35)
        self._entry_output.insert(0, "steam_library.csv")
        self._entry_output.grid(row=0, column=1, columnspan=2, sticky="ew")
        self._btn_browse = ttk.Button(exp, text="Browse...", command=self._browse_output)
        self._btn_browse._i18n_key = "btn_browse"
        self._btn_browse.grid(row=0, column=3, padx=(5, 0))

        self._lbl_format = ttk.Label(exp, text="Format:")
        self._lbl_format._i18n_key = "label_format"
        self._lbl_format.grid(row=1, column=0, sticky="e", padx=(0, 5))
        self._format_var = tk.StringVar(value="csv")
        f_frame = ttk.Frame(exp)
        f_frame.grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(f_frame, text="CSV", variable=self._format_var, value="csv").pack(side="left")
        ttk.Radiobutton(f_frame, text="JSON", variable=self._format_var, value="json").pack(side="left", padx=(8, 0))
        ttk.Radiobutton(f_frame, text="SQLite", variable=self._format_var, value="sqlite").pack(side="left", padx=(8, 0))
        self._format_var.trace_add("write", lambda *a: self._on_format_change())

        self._lbl_sort = ttk.Label(exp, text="Sort:")
        self._lbl_sort._i18n_key = "label_sort"
        self._lbl_sort.grid(row=1, column=2, sticky="e", padx=(15, 5))
        self._sort_var = tk.StringVar(value="playtime")
        SORT_KEYS = ["playtime", "playtime_2weeks", "name", "appid", "metacritic",
                     "reviews", "price", "release_date", "owners"]
        self._combo_sort = ttk.Combobox(
            exp, textvariable=self._sort_var,
            values=SORT_KEYS, state="readonly", width=12,
        )
        self._combo_sort.grid(row=1, column=3, sticky="w", padx=(0, 5))

        self._lbl_sort2 = ttk.Label(exp, text="Secondary:")
        self._lbl_sort2._i18n_key = "label_sort_secondary"
        self._lbl_sort2.grid(row=1, column=4, sticky="e", padx=(5, 5))
        SORT_KEYS2 = ["none", "playtime", "playtime_2weeks", "name", "appid",
                      "metacritic", "reviews", "price", "release_date", "owners"]
        self._sort2_var = tk.StringVar(value="none")
        self._combo_sort2 = ttk.Combobox(
            exp, textvariable=self._sort2_var,
            values=SORT_KEYS2, state="readonly", width=12,
        )
        self._combo_sort2.grid(row=1, column=5, sticky="w", padx=(0, 5))

        self._lbl_min = ttk.Label(exp, text="Min playtime (h):")
        self._lbl_min._i18n_key = "label_min_playtime"
        self._lbl_min.grid(row=2, column=0, sticky="e", padx=(0, 5))
        self._entry_min = ttk.Entry(exp, width=8)
        self._entry_min.insert(0, "0")
        self._entry_min.grid(row=2, column=1, sticky="w")

        self._lbl_limit = ttk.Label(exp, text="Limit:")
        self._lbl_limit._i18n_key = "label_limit"
        self._lbl_limit.grid(row=2, column=2, sticky="e", padx=(15, 5))
        self._entry_limit = ttk.Entry(exp, width=8)
        self._entry_limit.insert(0, "0")
        self._entry_limit.grid(row=2, column=3, sticky="w")
        self._lbl_limit_hint = ttk.Label(exp, text="(0=all)")
        self._lbl_limit_hint._i18n_key = "label_limit_hint"
        self._lbl_limit_hint.grid(row=2, column=4, sticky="w", padx=(3, 0))

        self._lbl_cols = ttk.Label(exp, text="Columns:")
        self._lbl_cols._i18n_key = "label_selected_cols"
        self._lbl_cols.grid(row=3, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        self._lbl_col_count = ttk.Label(exp, text="")
        self._lbl_col_count.grid(row=3, column=1, sticky="w", pady=(5, 0))
        self._btn_cols = ttk.Button(exp, text="Select Columns...", command=self._open_col_select)
        self._btn_cols._i18n_key = "btn_select_cols"
        self._btn_cols.grid(row=3, column=2, padx=(15, 0), pady=(5, 0))

        self._steamspy_var = tk.BooleanVar(value=True)
        self._chk_spy = ttk.Checkbutton(
            exp, text="Include SteamSpy data",
            variable=self._steamspy_var,
        )
        self._chk_spy._i18n_key = "chk_steamspy"
        self._chk_spy.grid(row=4, column=1, columnspan=2, sticky="w", pady=(5, 0))

        exp.columnconfigure(1, weight=1)
        exp.columnconfigure(3, weight=1)

        # ── Progress bar ──
        prog_frame = ttk.Frame(main)
        prog_frame.pack(fill="x", pady=(2, 5))

        self._prog_label = ttk.Label(prog_frame, text="Progress:")
        self._prog_label._i18n_key = "label_progress"
        self._prog_label.pack(side="left")
        self._progress = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self._progress.pack(side="left", fill="x", expand=True, padx=(5, 10))
        self._lbl_eta = ttk.Label(prog_frame, text="ETA: --")
        self._lbl_eta._i18n_key = "label_eta"
        self._lbl_eta.pack(side="right")

        # ── Buttons ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 5))

        self._btn_start = ttk.Button(btn_frame, text="▶ Start Export", command=self._start_export)
        self._btn_start._i18n_key = "btn_start"
        self._btn_start.pack(side="left", padx=(0, 5))

        self._btn_cancel = ttk.Button(btn_frame, text="■ Cancel", command=self._cancel_export, state="disabled")
        self._btn_cancel._i18n_key = "btn_cancel"
        self._btn_cancel.pack(side="left", padx=(0, 5))

        self._btn_open = ttk.Button(btn_frame, text="Open File Location", command=self._open_file_location)
        self._btn_open._i18n_key = "btn_open_file"
        self._btn_open.pack(side="left")

        self._btn_clear = ttk.Button(btn_frame, text="Clear Log", command=self._clear_log)
        self._btn_clear._i18n_key = "btn_clear_log"
        self._btn_clear.pack(side="right")

        # ── Log area ──
        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            log_frame, wrap="word", state="disabled",
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._load_env()
        self._update_col_count()

    # ── Environment ─────────────────────────────────────────────────

    def _load_env(self):
        self.env_data = EnvManager.load()
        self._entry_key.configure(state="normal")
        self._entry_key.delete(0, "end")
        self._entry_key.insert(0, self.env_data.get("STEAM_API_KEY", ""))
        self._entry_key.configure(state="readonly")
        self._entry_sid.configure(state="normal")
        self._entry_sid.delete(0, "end")
        self._entry_sid.insert(0, self.env_data.get("STEAM_ID", ""))
        self._entry_sid.configure(state="readonly")

        sel_str = self.env_data.get("SELECTED_COLUMNS", "")
        if sel_str:
            self.selected_columns = set(
                c.strip() for c in sel_str.split(",") if c.strip() in ALL_COLUMNS
            )
        else:
            self.selected_columns = set(ALL_COLUMNS)

        lang = self.env_data.get("LANGUAGE", "zh")
        if lang != self.i18n.lang:
            self.i18n.lang = lang
            self._apply_language()

        theme = self.env_data.get("THEME", "clam")
        available = ttk.Style().theme_names()
        if theme in available:
            ttk.Style().theme_use(theme)

        self._update_col_count()

    def _save_env(self):
        env = dict(self.env_data)
        env["SELECTED_COLUMNS"] = ",".join(sorted(self.selected_columns))
        EnvManager.save(env)

    # ── Dialogs ──────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self.root, self.i18n, self.env_data)

    def _open_col_select(self):
        dlg = ColumnSelectDialog(self.root, self.i18n, self.selected_columns)
        self.root.wait_window(dlg)
        if dlg.result is not None:
            self.selected_columns = dlg.result
            self._save_env()
            self._update_col_count()

    def _browse_output(self):
        fmt = self._format_var.get()
        ext_map = {"csv": ".csv", "json": ".json", "sqlite": ".db"}
        type_map = {
            "csv": [("CSV files", "*.csv"), ("All files", "*.*")],
            "json": [("JSON files", "*.json"), ("All files", "*.*")],
            "sqlite": [("SQLite files", "*.db"), ("All files", "*.*")],
        }
        path = filedialog.asksaveasfilename(
            defaultextension=ext_map.get(fmt, ".csv"),
            filetypes=type_map.get(fmt, [("All files", "*.*")]),
            initialfile=f"steam_library{ext_map.get(fmt, '.csv')}",
        )
        if path:
            self._entry_output.delete(0, "end")
            self._entry_output.insert(0, path)

    def _on_format_change(self):
        fmt = self._format_var.get()
        ext_map = {"csv": ".csv", "json": ".json", "sqlite": ".db"}
        current = self._entry_output.get().strip()
        if current:
            self._entry_output.delete(0, "end")
            self._entry_output.insert(0, str(Path(current).with_suffix(ext_map.get(fmt, ".csv"))))

    def _update_col_count(self):
        total = len(ALL_COLUMNS)
        sel = len(self.selected_columns)
        self._lbl_col_count.configure(
            text=self.i18n.t("label_total_selected").replace("{}/{}", f"{sel}/{total}")
        )

    # ── Export ───────────────────────────────────────────────────────

    def _start_export(self):
        api_key = self.env_data.get("STEAM_API_KEY", "")
        steam_id = self.env_data.get("STEAM_ID", "")

        if not api_key or not steam_id:
            messagebox.showwarning(
                self.i18n.t("window_title"),
                self.i18n.t("msg_validation_fail"),
            )
            return

        output = self._entry_output.get().strip()
        if not output:
            fmt = self._format_var.get()
            ext_map = {"csv": ".csv", "json": ".json", "sqlite": ".db"}
            output = f"steam_library{ext_map.get(fmt, '.csv')}"
            self._entry_output.delete(0, "end")
            self._entry_output.insert(0, output)

        sort2 = self._sort2_var.get()
        cfg = {
            "key": api_key,
            "steamid": steam_id,
            "output": output,
            "format": self._format_var.get(),
            "sort": self._sort_var.get(),
            "sort_secondary": sort2 if sort2 != "none" else None,
            "min_playtime": float(self._entry_min.get() or 0),
            "limit": int(self._entry_limit.get() or 0),
            "no_steamspy": not self._steamspy_var.get(),
        }

        self._cancel_event.clear()
        self._export_running = True
        self._set_controls_state("disabled")
        self._btn_cancel.configure(state="normal")
        self._progress["value"] = 0
        self._progress["maximum"] = 100

        self._export_thread = threading.Thread(
            target=self._run_export_thread, args=(cfg,), daemon=True,
        )
        self._export_thread.start()

    def _run_export_thread(self, cfg: dict):
        try:
            result = run_export(
                cfg,
                log_callback=self._log_safe,
                progress_callback=self._progress_safe,
                cancel_event=self._cancel_event,
                selected_columns=set(self.selected_columns) if self.selected_columns else None,
            )
            if result is not None:
                self._root_after(lambda: self._on_export_done(cfg["output"]))
            else:
                self._root_after(self._on_export_cancelled)
        except Exception as e:
            if self._cancel_event.is_set():
                self._root_after(self._on_export_cancelled)
            else:
                error_msg = str(e)
                self._root_after(lambda msg=error_msg: self._on_export_error(msg))

    def _cancel_export(self):
        if not self._export_running:
            return
        ok = messagebox.askyesno(
            self.i18n.t("window_title"),
            self.i18n.t("msg_confirm_cancel"),
        )
        if ok:
            self._cancel_event.set()
            self._log_safe("[取消] 正在停止...")

    def _on_export_done(self, output_path: str):
        self._export_running = False
        self._set_controls_state("normal")
        self._progress["value"] = 100
        self._lbl_eta.configure(text="ETA: --")
        self._btn_cancel.configure(state="disabled")

        msg = self.i18n.t("msg_export_done")
        messagebox.showinfo(self.i18n.t("window_title"), f"{msg} -> {output_path}")
        self._log_safe(f"\n{'=' * 50}")
        self._log_safe(f" {msg}")
        self._log_safe(f" 文件: {output_path}")
        self._log_safe(f"{'=' * 50}")

    def _on_export_cancelled(self):
        self._export_running = False
        self._set_controls_state("normal")
        self._btn_cancel.configure(state="disabled")
        self._lbl_eta.configure(text="ETA: --")
        self._log_safe("[取消] 用户中断导出")

    def _on_export_error(self, error_msg: str):
        self._export_running = False
        self._set_controls_state("normal")
        self._btn_cancel.configure(state="disabled")
        self._lbl_eta.configure(text="ETA: --")
        self._log_safe(f"[ERROR] {error_msg}")
        messagebox.showerror(self.i18n.t("window_title"), error_msg)

    def _set_controls_state(self, state: str):
        controls = [
            self._entry_output, self._btn_browse, self._combo_sort,
            self._combo_sort2,
            self._entry_min, self._entry_limit, self._btn_cols,
            self._btn_settings, self._btn_start,
        ]
        for c in controls:
            try:
                c.configure(state=state)
            except Exception:
                pass
        for child in self.root.winfo_children():
            for c in child.winfo_children():
                if isinstance(c, (ttk.Radiobutton, ttk.Checkbutton)):
                    try:
                        c.configure(state=state if state != "disabled" else "disabled")
                    except Exception:
                        pass

    # ── Thread-safe UI ───────────────────────────────────────────────

    def _log_safe(self, msg: str):
        self._root_after(lambda: self._append_log(msg))

    def _progress_safe(self, current: int, total: int, name: str, eta: str):
        self._root_after(lambda: self._update_progress(current, total, name, eta))

    def _root_after(self, func):
        try:
            self.root.after(1, func)
        except Exception:
            pass

    def _append_log(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _update_progress(self, current: int, total: int, name: str, eta: str):
        if total > 0:
            self._progress["maximum"] = total
            self._progress["value"] = current
        self._lbl_eta.configure(text=f"ETA: {eta}")

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    def _open_file_location(self):
        output = self._entry_output.get().strip()
        if not output:
            output = f"steam_library.{self._format_var.get()}"
        path = BASE_DIR / output
        target = path.parent if path.exists() else Path(os.path.dirname(str(path)))
        try:
            if sys.platform == "win32":
                os.startfile(target)
            else:
                import subprocess
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(target)])
        except Exception as e:
            self._append_log(f"[ERROR] 无法打开文件位置: {e}")

    # ── Language ─────────────────────────────────────────────────────

    def _apply_language(self):
        i = self.i18n
        self.root.title(i.t("window_title"))
        self._apply_lang_widget(self.root, i)
        self._update_col_count()

    def _apply_lang_widget(self, widget, i):
        key = getattr(widget, "_i18n_key", None)
        if key:
            try:
                widget.configure(text=i.t(key))
            except tk.TclError:
                pass
        if isinstance(widget, ttk.LabelFrame):
            sk = getattr(widget, "_i18n_key", None)
            if sk:
                widget.configure(text=i.t(sk))
        for child in widget.winfo_children():
            self._apply_lang_widget(child, i)

    def _on_close(self):
        if self._export_running:
            self._cancel_event.set()
            if self._export_thread and self._export_thread.is_alive():
                self._export_thread.join(timeout=3)
        self.root.destroy()
