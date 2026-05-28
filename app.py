from flask import Flask, render_template, request, redirect, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
DB_NAME = "posts.db"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            file_name TEXT,
            saved_file_name TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL,
            file_name TEXT,
            saved_file_name TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    search_type = request.args.get("search_type", "title")
    keyword = request.args.get("keyword", "")

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db()

    if keyword:
        if search_type == "author":
            where = "WHERE author LIKE ?"
        else:
            where = "WHERE title LIKE ?"

        total = conn.execute(
            f"SELECT COUNT(*) FROM posts {where}",
            (f"%{keyword}%",)
        ).fetchone()[0]

        posts = conn.execute(
            f"SELECT * FROM posts {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (f"%{keyword}%", per_page, offset)
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

        posts = conn.execute(
            "SELECT * FROM posts ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "index.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
        search_type=search_type,
        keyword=keyword
    )


@app.route("/write", methods=["GET", "POST"])
def write():
    if request.method == "POST":
        author = request.form["author"]
        title = request.form["title"]
        content = request.form["content"]

        uploaded_file = request.files.get("file")
        file_name = None
        saved_file_name = None

        if uploaded_file and uploaded_file.filename != "":
            file_name = secure_filename(uploaded_file.filename)
            ext = os.path.splitext(file_name)[1]
            saved_file_name = f"{uuid4().hex}{ext}"
            uploaded_file.save(os.path.join(UPLOAD_FOLDER, saved_file_name))

        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = get_db()
        conn.execute("""
            INSERT INTO posts (title, author, content, date, views, file_name, saved_file_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, content, date, 0, file_name, saved_file_name))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("write.html")


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    conn = get_db()

    post = conn.execute(
        "SELECT * FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if post is None:
        conn.close()
        return "게시글을 찾을 수 없습니다."

    if request.method == "POST":
        author = request.form["author"]
        title = request.form["title"]
        content = request.form["content"]
        delete_file = request.form.get("delete_file")

        if delete_file == "on" and post["saved_file_name"]:
            file_path = os.path.join(UPLOAD_FOLDER, post["saved_file_name"])

            if os.path.exists(file_path):
                os.remove(file_path)

            conn.execute("""
                UPDATE posts
                SET author = ?, title = ?, content = ?, file_name = NULL, saved_file_name = NULL
                WHERE id = ?
            """, (author, title, content, post_id))
        else:
            conn.execute("""
                UPDATE posts
                SET author = ?, title = ?, content = ?
                WHERE id = ?
            """, (author, title, content, post_id))

        conn.commit()
        conn.close()

        return redirect(f"/post/{post_id}")

    conn.close()
    return render_template("edit.html", post=post)


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    conn = get_db()

    conn.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    conn.commit()

    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()

    comments = conn.execute(
        "SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC",
        (post_id,)
    ).fetchall()

    conn.close()

    if post is None:
        return "게시글을 찾을 수 없습니다."

    return render_template("post.html", post=post, comments=comments)


@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    author = request.form["author"]
    content = request.form["content"]

    uploaded_file = request.files.get("file")
    file_name = None
    saved_file_name = None

    if uploaded_file and uploaded_file.filename != "":
        file_name = secure_filename(uploaded_file.filename)
        ext = os.path.splitext(file_name)[1]
        saved_file_name = f"{uuid4().hex}{ext}"
        uploaded_file.save(os.path.join(UPLOAD_FOLDER, saved_file_name))

    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    conn.execute("""
        INSERT INTO comments (post_id, author, content, date, file_name, saved_file_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (post_id, author, content, date, file_name, saved_file_name))
    conn.commit()
    conn.close()

    return redirect(f"/post/{post_id}")


@app.route("/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    conn = get_db()

    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    comments = conn.execute("SELECT * FROM comments WHERE post_id = ?", (post_id,)).fetchall()

    if post:
        if post["saved_file_name"]:
            file_path = os.path.join(UPLOAD_FOLDER, post["saved_file_name"])
            if os.path.exists(file_path):
                os.remove(file_path)

        for comment in comments:
            if comment["saved_file_name"]:
                file_path = os.path.join(UPLOAD_FOLDER, comment["saved_file_name"])
                if os.path.exists(file_path):
                    os.remove(file_path)

        conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/delete_comment/<int:comment_id>/<int:post_id>", methods=["POST"])
def delete_comment(comment_id, post_id):
    conn = get_db()

    comment = conn.execute(
        "SELECT * FROM comments WHERE id = ?",
        (comment_id,)
    ).fetchone()

    if comment:
        if comment["saved_file_name"]:
            file_path = os.path.join(UPLOAD_FOLDER, comment["saved_file_name"])
            if os.path.exists(file_path):
                os.remove(file_path)

        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()

    conn.close()
    return redirect(f"/post/{post_id}")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)