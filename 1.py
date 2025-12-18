"""
Single-file Django blog (blog_db.sqlite)
Requirements:
  pip install Django
Run:
  python django_blog_single_file.py runserver

This file uses Django for URL routing and templating but uses sqlite3 directly for storage
so you don't need Django migrations. Templates and CSS are embedded via the locmem loader.
"""
import os
import sys
import sqlite3
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'blog_db.sqlite'

DEBUG = True
SECRET_KEY = 'single-file-blog-secret'
ALLOWED_HOSTS = ['*']

TEMPLATES = {
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': False,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
        ],
        'loaders': [
            ('django.template.loaders.locmem.Loader', {
                'base.html': """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{% block title %}My Blog{% endblock %}</title>
  <style>
    /* Simple, responsive blog CSS */
    body{font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin:0; padding:0; background:#f7f7fb; color:#111}
    header{background:linear-gradient(90deg,#4f46e5,#06b6d4); color:white; padding:28px 18px}
    .container{max-width:900px;margin:24px auto;padding:0 18px}
    h1{margin:0;font-size:28px}
    .post{background:white;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 6px 18px rgba(15,23,42,0.06)}
    .meta{color:#6b7280;font-size:13px;margin-bottom:10px}
    a{color:#334155;text-decoration:none}
    .actions{margin-top:12px}
    form input[type=text], form textarea{width:100%;padding:10px;border:1px solid #e6e9ee;border-radius:8px;margin-bottom:8px}
    .btn{display:inline-block;padding:8px 12px;border-radius:8px;border:0;background:#4f46e5;color:white;cursor:pointer}
    .btn.ghost{background:transparent;color:#374151;border:1px solid #e6e9ee}
    footer{color:#6b7280;font-size:13px;text-align:center;padding:24px 0}
    @media (max-width:640px){h1{font-size:22px}}
  </style>
</head>
<body>
  <header>
    <div class="container">
      <h1><a href="/" style="color:inherit;text-decoration:none">My Single-file Django Blog</a></h1>
    </div>
  </header>
  <main class="container">
    {% block content %}{% endblock %}
  </main>
  <footer>
    <div class="container">
      <p>Made with ❤️ — Single-file Django + sqlite3</p>
    </div>
  </footer>
</body>
</html>
""",
                'index.html': """
{% extends 'base.html' %}
{% block title %}Home - My Blog{% endblock %}
{% block content %}
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h2>Latest posts</h2>
    <div><a href="/create/" class="btn">Create Post</a></div>
  </div>
  {% if posts %}
    {% for p in posts %}
      <article class="post">
        <div class="meta">{{ p.created_at }} • {{ p.author or 'Anonymous' }}</div>
        <h3><a href="/post/{{ p.id }}/">{{ p.title }}</a></h3>
        <p>{{ p.excerpt }}</p>
        <div class="actions">
          <a href="/post/{{ p.id }}/" class="btn">Read</a>
          <a href="/edit/{{ p.id }}/" class="btn ghost">Edit</a>
          <a href="/delete/{{ p.id }}/" onclick="return confirm('Delete this post?')" class="btn ghost">Delete</a>
        </div>
      </article>
    {% endfor %}
  {% else %}
    <p>No posts yet — <a href="/create/">create the first post</a>.</p>
  {% endif %}
{% endblock %}
""",
                'post.html': """
{% extends 'base.html' %}
{% block title %}{{ post.title }} - My Blog{% endblock %}
{% block content %}
  <article class="post">
    <div class="meta">{{ post.created_at }} • {{ post.author or 'Anonymous' }}</div>
    <h2>{{ post.title }}</h2>
    <div style="white-space:pre-wrap;margin-top:12px">{{ post.content }}</div>
    <div class="actions">
      <a href="/edit/{{ post.id }}/" class="btn ghost">Edit</a>
      <a href="/delete/{{ post.id }}/" onclick="return confirm('Delete this post?')" class="btn ghost">Delete</a>
      <a href="/" class="btn">Back</a>
    </div>
  </article>
{% endblock %}
""",
                'form.html': """
{% extends 'base.html' %}
{% block title %}{{ mode }} Post - My Blog{% endblock %}
{% block content %}
  <div class="post">
    <form method="post" action="{{ action }}">
      <input type="text" name="title" placeholder="Title" value="{{ post.title|default_if_none:'' }}" required>
      <input type="text" name="author" placeholder="Author" value="{{ post.author|default_if_none:'' }}">
      <textarea name="content" rows="10" placeholder="Write your post" required>{{ post.content|default_if_none:'' }}</textarea>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn" type="submit">{{ mode }}</button>
        <a href="/" class="btn ghost">Cancel</a>
      </div>
    </form>
  </div>
{% endblock %}
""",
                'confirm_delete.html': """
{% extends 'base.html' %}
{% block content %}
  <div class="post">
    <h3>Delete Post</h3>
    <p>Are you sure you want to delete "{{ post.title }}"?</p>
    <form method="post" action="{{ action }}">
      <button class="btn">Delete</button>
      <a href="/" class="btn ghost">Cancel</a>
    </form>
  </div>
{% endblock %}
""",
            }),],
    },
}

settings.configure(
    DEBUG=DEBUG,
    SECRET_KEY=SECRET_KEY,
    ALLOWED_HOSTS=ALLOWED_HOSTS,
    ROOT_URLCONF=__name__,
    TEMPLATES=[TEMPLATES],
)

# Import django after settings configured
import django
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import escape

django.setup()

# --- Database helpers (sqlite3) ---

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()

# Utility: excerpt

def excerpt(text, n=220):
    t = text.strip()
    if len(t) <= n:
        return t
    return t[:n].rsplit(' ', 1)[0] + '...'

# --- Views ---

def index(request):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id,title,author,content,created_at FROM posts ORDER BY id DESC")
    rows = c.fetchall()
    posts = []
    for r in rows:
        posts.append({
            'id': r['id'],
            'title': r['title'],
            'author': r['author'],
            'content': r['content'],
            'excerpt': excerpt(r['content'], 200),
            'created_at': r['created_at'],
        })
    tpl = loader.get_template('index.html')
    return HttpResponse(tpl.render({'posts': posts}, request))


def view_post(request, post_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id,title,author,content,created_at FROM posts WHERE id=?", (post_id,))
    r = c.fetchone()
    if not r:
        raise Http404('Post not found')
    post = dict(r)
    tpl = loader.get_template('post.html')
    return HttpResponse(tpl.render({'post': post}, request))


def create_post(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip() or None
        content = request.POST.get('content', '').strip()
        if not title or not content:
            return HttpResponse('Title and content required', status=400)
        conn = get_connection()
        c = conn.cursor()
        from datetime import datetime
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        c.execute('INSERT INTO posts (title,author,content,created_at) VALUES (?,?,?,?)', (title, author, content, now))
        conn.commit()
        conn.close()
        return redirect('/')
    else:
        tpl = loader.get_template('form.html')
        return HttpResponse(tpl.render({'mode': 'Create', 'action': '/create/', 'post': {}}, request))


def edit_post(request, post_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id,title,author,content,created_at FROM posts WHERE id=?", (post_id,))
    r = c.fetchone()
    if not r:
        raise Http404('Post not found')
    post = dict(r)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip() or None
        content = request.POST.get('content', '').strip()
        if not title or not content:
            return HttpResponse('Title and content required', status=400)
        c.execute('UPDATE posts SET title=?,author=?,content=? WHERE id=?', (title, author, content, post_id))
        conn.commit()
        conn.close()
        return redirect(f'/post/{post_id}/')
    else:
        tpl = loader.get_template('form.html')
        return HttpResponse(tpl.render({'mode': 'Edit', 'action': f'/edit/{post_id}/', 'post': post}, request))


def delete_post(request, post_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id,title FROM posts WHERE id=?", (post_id,))
    r = c.fetchone()
    if not r:
        raise Http404('Post not found')
    post = dict(r)
    if request.method == 'POST':
        c.execute('DELETE FROM posts WHERE id=?', (post_id,))
        conn.commit()
        conn.close()
        return redirect('/')
    tpl = loader.get_template('confirm_delete.html')
    return HttpResponse(tpl.render({'post': post, 'action': f'/delete/{post_id}/'}, request))


# --- URL configuration ---
urlpatterns = [
    path('', index),
    path('post/<int:post_id>/', view_post),
    path('create/', create_post),
    path('edit/<int:post_id>/', edit_post),
    path('delete/<int:post_id>/', delete_post),
]

# --- Runserver support ---
if __name__ == '__main__':
    # Ensure Django's command-line runner is available
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
