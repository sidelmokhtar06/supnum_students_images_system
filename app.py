import hmac
import io
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from i18n import LANGS, TEXT

register_heif_opener()  # lets Pillow open iPhone HEIC photos

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MATRICULE_RE = re.compile(r"^26\d{3,6}$")  # promo 2026: "26" + digits
MAX_SIDE = 1200  # px, photos are resized so the longest side fits

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # raw phone photos can be big; we shrink them
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # blocks cross-site POSTs to admin actions
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def photos():
    return sorted(p.name for p in UPLOAD_DIR.iterdir() if p.is_file())


def require_admin():
    if not session.get("admin"):
        abort(redirect(url_for("login")))


def is_taken(matricule):
    return any(UPLOAD_DIR.glob(f"{matricule}.*"))


def lang():
    """Student page language: ?lang=, then the saved cookie, then the browser's language, else French."""
    choice = request.args.get("lang") or request.cookies.get("lang") or request.accept_languages.best_match(LANGS)
    return choice if choice in LANGS else "fr"


def t(key, **kw):
    return TEXT[lang()][key].format(**kw)


@app.after_request
def remember_lang(response):
    if request.args.get("lang") in LANGS:
        response.set_cookie("lang", request.args["lang"], max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def check_matricule(matricule):
    """Return an error message, or None if the matricule can be used."""
    if not MATRICULE_RE.match(matricule):
        return t("err_invalid")
    if is_taken(matricule):
        return t("err_taken", m=matricule)
    return None


@app.route("/check/<matricule>")
def check(matricule):
    error = check_matricule(matricule)
    return {"ok": error is None, "error": error}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        matricule = request.form.get("matricule", "").strip().upper()
        file = request.files.get("photo")
        error = check_matricule(matricule)
        if error:
            flash(error, "error")
        elif not file:
            flash(t("err_nophoto"), "error")
        else:
            try:
                img = ImageOps.exif_transpose(Image.open(file.stream))  # fix phone rotation
                img = img.convert("RGB")
                img.thumbnail((MAX_SIDE, MAX_SIDE))
            except Exception:
                flash(t("err_badimg"), "error")
                return redirect(url_for("index"))
            try:
                # "xb" fails if the file already exists, so two simultaneous uploads can't overwrite each other.
                with open(UPLOAD_DIR / f"{matricule}.jpg", "xb") as out:
                    img.save(out, "JPEG", quality=85)
            except FileExistsError:
                flash(t("err_taken", m=matricule), "error")
                return redirect(url_for("index"))
            flash(t("ok_saved", m=matricule), "ok")
        return redirect(url_for("index"))
    return render_template("index.html", lang=lang(), t=TEXT[lang()])


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Mot de passe incorrect.", "error")
    return render_template("login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
def admin():
    require_admin()
    items = [(n, (UPLOAD_DIR / n).stat().st_mtime) for n in photos()]
    items.sort(key=lambda it: it[1], reverse=True)  # newest first
    return render_template("admin.html", items=items, datetime=datetime)


@app.route("/admin/photo/<name>")
def photo(name):
    require_admin()
    return send_from_directory(UPLOAD_DIR, name, as_attachment="dl" in request.args)


def existing_photo(name):
    if name not in photos():
        abort(404)
    return UPLOAD_DIR / name


@app.post("/admin/delete")
def delete():
    require_admin()
    existing_photo(request.form["name"]).unlink()
    flash(f"{request.form['name']} supprimée.", "ok")
    return redirect(url_for("admin"))


@app.post("/admin/rename")
def rename():
    require_admin()
    src = existing_photo(request.form["name"])
    matricule = request.form.get("matricule", "").strip().upper()
    if not MATRICULE_RE.match(matricule):
        flash("Matricule invalide.", "error")
    elif is_taken(matricule):
        flash(f"Une photo existe déjà pour {matricule}.", "error")
    else:
        src.rename(UPLOAD_DIR / f"{matricule}{src.suffix}")
        flash(f"{src.stem} renommée en {matricule}.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/download-all")
def download_all():
    require_admin()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in photos():
            zf.write(UPLOAD_DIR / name, name)
    buf.seek(0)
    return send_file(buf, download_name="supnum_photos.zip", as_attachment=True)


@app.errorhandler(413)
def too_large(_):
    flash(t("err_toobig"), "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
