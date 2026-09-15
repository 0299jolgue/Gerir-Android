"""Painel web de demonstração para gerir dispositivos Android empresariais."""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "gerir_android.db"

SEED_DEVICES = (
    ("UGPhone QA-01", "ugphone-qa-01", "Android 13", "online", 82, "São Paulo", "Há segundos"),
    ("LDPhone Teste-02", "ldphone-test-02", "Android 12", "online", 64, "Lisboa", "Há 1 min"),
    ("Emulador Financeiro", "finance-03", "Android 14", "locked", 41, "Porto", "Há 4 min"),
    ("Tablet Armazém", "warehouse-04", "Android 11", "offline", 19, "Braga", "Há 2 h"),
)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database() -> None:
    connection = get_db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            identifier TEXT NOT NULL UNIQUE,
            android_version TEXT NOT NULL,
            status TEXT NOT NULL,
            battery INTEGER NOT NULL,
            location TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            screen_state TEXT NOT NULL DEFAULT 'unlocked',
            notifications INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES devices(id)
        );
        """
    )
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    if not connection.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        connection.execute("INSERT INTO users VALUES (?, ?)", (username, generate_password_hash(password)))
    if not connection.execute("SELECT 1 FROM devices LIMIT 1").fetchone():
        connection.executemany(
            """INSERT INTO devices
            (name, identifier, android_version, status, battery, location, last_seen, screen_state, notifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(name, identifier, version, status, battery, location, seen, "locked" if status == "locked" else "unlocked", 2 if status == "online" else 0)
             for name, identifier, version, status, battery, location, seen in SEED_DEVICES],
        )
    connection.commit()
    connection.close()


def login_required(view):
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def record_event(connection: sqlite3.Connection, device_id: int, event_type: str, detail: str) -> None:
    connection.execute(
        "INSERT INTO events (device_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
        (device_id, event_type, detail, utc_now()),
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    initialise_database()

    @app.get("/")
    @login_required
    def dashboard():
        connection = get_db()
        counts = connection.execute(
            "SELECT COUNT(*) AS total, SUM(status = 'online') AS online, SUM(status = 'locked') AS locked, SUM(status = 'offline') AS offline FROM devices"
        ).fetchone()
        devices = connection.execute("SELECT * FROM devices ORDER BY id LIMIT 4").fetchall()
        connection.close()
        return render_template("dashboard.html", counts=counts, devices=devices)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            connection = get_db()
            user = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            connection.close()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["username"] = username
                return redirect(url_for("dashboard"))
            flash("Credenciais inválidas.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/devices")
    @login_required
    def devices():
        connection = get_db()
        rows = connection.execute("SELECT * FROM devices ORDER BY name").fetchall()
        connection.close()
        return render_template("devices.html", devices=rows)

    @app.get("/devices/<int:device_id>")
    @login_required
    def device_detail(device_id: int):
        connection = get_db()
        device = connection.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        events = connection.execute("SELECT * FROM events WHERE device_id = ? ORDER BY id DESC LIMIT 8", (device_id,)).fetchall()
        connection.close()
        if not device:
            abort(404)
        return render_template("device_detail.html", device=device, events=events)

    @app.post("/devices/<int:device_id>/command")
    @login_required
    def command(device_id: int):
        payload = request.get_json(silent=True) or request.form
        action = payload.get("action")
        message = (payload.get("message") or "").strip()
        connection = get_db()
        device = connection.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if not device:
            connection.close()
            abort(404)
        if action == "lock":
            connection.execute("UPDATE devices SET screen_state = 'locked', status = 'locked' WHERE id = ?", (device_id,))
            detail = "Comando de bloqueio registado (simulado)."
        elif action == "unlock":
            connection.execute("UPDATE devices SET screen_state = 'unlocked', status = 'online' WHERE id = ?", (device_id,))
            detail = "Pedido de desbloqueio registado (simulado)."
        elif action == "message" and message:
            detail = f"Mensagem preparada para envio: {message[:160]}"
        else:
            connection.close()
            return jsonify({"ok": False, "message": "Comando inválido."}), 400
        record_event(connection, device_id, action, detail)
        connection.commit()
        connection.close()
        return jsonify({"ok": True, "message": detail})

    @app.get("/devices/<int:device_id>/status")
    @login_required
    def device_status(device_id: int):
        connection = get_db()
        device = connection.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        connection.close()
        if not device:
            abort(404)
        return jsonify({"status": device["status"], "battery": device["battery"], "screen_state": device["screen_state"], "updated_at": utc_now()})

    @app.route("/apk", methods=["GET", "POST"])
    @login_required
    def apk():
        if request.method == "POST":
            flash("Configuração do agente gerada. A compilação do APK real requer o projeto Android e uma chave de assinatura protegida.", "success")
        return render_template("apk.html")

    return app
