#!/usr/bin/env python3
"""Export a Claude Slides deck to one self-contained, interactive HTML deck.

The output uses the same viewer as the other ClinVar-GKM presentations in
`docs/assets/presentations/`: a 1920x1080 stage scaled to fit, a progress bar,
speaker notes, light/dark themes and keyboard shortcuts. It has no external
dependencies, so it works offline and inside the docs iframe.

Input is the deck's `project/` folder from its Slides artifact: `deck.json`
(slide order and title), `deck.css` (shared slide styles) and
`slides/<id>.html` (one `<section>` per slide, notes in `<aside>`). Download it
from the artifact (for "Strict Profiles, Fast Tables":
https://claude.ai/artifact/GFb6RqoYHYwbxULM5148Nu), then run:

    python3 -I src/scripts/export-slides-deck.py <project dir> \
        docs/assets/presentations/clinvar-gkm-strict-profiles.html

Check the changed slides in both themes (`T`) before committing.
"""
import html
import json
import re
import sys

if len(sys.argv) != 3:
    sys.exit("usage: export-slides-deck.py <deck project dir> <out.html>")
proj, out = sys.argv[1], sys.argv[2]
deck = json.load(open(f"{proj}/deck.json"))
css = open(f"{proj}/deck.css").read()

ARROW = ('<svg width="80" height="40" viewBox="0 0 80 40" aria-hidden="true">'
         '<path d="M0 12h48V0l32 20-32 20V28H0z" fill="var(--brand-primary)"/></svg>')

# Inline colours that must follow the theme.
RECOLOR = {
    "color:#212529;": "color:var(--ink);",
    'color:#19692c;': "color:var(--status-released-fg);",
    'color:#0f6674;': "color:var(--status-beta-fg);",
    'color:#495057;': "color:var(--status-planned-fg);",
}

slides = []
for sid in deck["order"]:
    s = open(f"{proj}/slides/{sid}.html").read().strip()
    s = re.sub(r'<x-shape kind="arrow-right"[^>]*></x-shape>', ARROW, s)
    for a, b in RECOLOR.items():
        s = s.replace(a, b)
    # <section id=.. class=..> -> add the viewer's "slide" class
    m = re.match(r'<section([^>]*)>', s)
    attrs = m.group(1)
    attrs = re.sub(r'\s*data-transition="[^"]*"', "", attrs)
    if 'class="' in attrs:
        attrs = attrs.replace('class="', 'class="slide ', 1)
    else:
        attrs += ' class="slide"'
    s = f"<section{attrs}>" + s[m.end():]
    # speaker notes: plain-text <aside> -> hidden .snotes block
    s = re.sub(r'<aside>(.*?)</aside>',
               lambda mm: f'<aside class="snotes" hidden><p>{mm.group(1)}</p></aside>',
               s, flags=re.S)
    if sid == deck.get("cover", "cover"):
        s = s.replace("</aside>", "</aside>", 1)
        s = s.replace(
            '<aside class="snotes"',
            '<p class="hint">Use ← / → to navigate · press ? for shortcuts</p>\n<aside class="snotes"', 1)
    slides.append(s)

title = deck["title"]

VIEWER_CSS = r"""
/* ---- Dark theme: the ClinGen palette, re-toned (T toggles) ---- */
:root[data-theme="dark"] {
  --brand-logo: #9cc0f2; --brand-primary: #6fc3e3; --brand-navy: #0e2440;
  --ink: #e7e9ec; --ink-secondary: #a7b0ba;
  --surface-100: #141a21; --surface-200: #1b222a; --surface-300: #1f2730;
  --border: #36404b; --border-strong: #4b5560;
  --status-released-fg: #8fd19e; --status-released-bg: #1e3a27;
  --status-beta-fg: #8ed8e6; --status-beta-bg: #123b44;
  --status-planned-fg: #c3cad2; --status-planned-bg: #2b323a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --brand-logo: #9cc0f2; --brand-primary: #6fc3e3; --brand-navy: #0e2440;
    --ink: #e7e9ec; --ink-secondary: #a7b0ba;
    --surface-100: #141a21; --surface-200: #1b222a; --surface-300: #1f2730;
    --border: #36404b; --border-strong: #4b5560;
    --status-released-fg: #8fd19e; --status-released-bg: #1e3a27;
    --status-beta-fg: #8ed8e6; --status-beta-bg: #123b44;
    --status-planned-fg: #c3cad2; --status-planned-bg: #2b323a;
  }
}
/* Filled blocks keep a deep blue ground in both themes. */
.card.strong, .step.us, .b3 { background: #19448d; border-color: #19448d; }
.card.strong .k, .card.strong h3, .card.strong .d, .step.us .name, .step.us .adds,
.b3 h3, .b3 .bt, .b3 .bx { color: #ffffff; }
.pill.inv { background: #ffffff; color: #19448d; }

/* ---- Slide format defaults (no default margins; tables draw hairlines) ---- */
* { box-sizing: border-box; }
:where(.slide p, .slide h1, .slide h2, .slide h3, .slide ul) { margin: 0; }
:where(.slide ul) { margin-top: 4px; }
.slide a { color: var(--brand-primary); }
.t { border-collapse: collapse; }
.t th, .t td { text-align: left; vertical-align: top; padding: 0.35em 0.6em; border-bottom: 1px solid var(--border); }
.t th { font-weight: 700; }
.t.tight th, .t.tight td { padding: 6px 14px; }
.hint { position: absolute; right: 128px; bottom: 96px; font-size: 24px; color: #ffffff; opacity: .85; }

/* ---- Viewer chrome (shared engine with the other ClinVar-GKM decks) ---- */
:root { --bg: var(--surface-300); --panel: var(--surface-200); --box: var(--surface-100);
  --line: var(--border); --accent: var(--brand-primary); --ink-soft: var(--ink-secondary);
  --shadow: 0 8px 30px rgba(20,28,40,.14); }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--ink); overflow: hidden; }
body { counter-reset: page; }
#viewport { position: fixed; inset: 0; display: grid; place-items: center; overflow: hidden; }
#stage { position: relative; width: 1920px; height: 1080px; transform: scale(var(--scale, 1));
  transform-origin: center center; flex: none; }
.slide { position: absolute; inset: 0; opacity: 0; visibility: hidden; transition: opacity .35s ease;
  border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow); overflow: hidden; }
.slide.active { opacity: 1; visibility: visible; }
.slide:not(.active) .anim { animation: none; }
@media (prefers-reduced-motion: reduce) { .slide { transition: none; } .anim { animation: none !important; } }

#prog { position: fixed; left: 0; top: 0; height: 4px; width: 100%; z-index: 30; }
#prog > i { display: block; height: 100%; width: 0; background: var(--accent); transition: width .3s ease; }
#counter { position: fixed; right: 16px; bottom: 12px; font-size: 13px; color: var(--ink-soft);
  font-family: ui-monospace, monospace; z-index: 30; background: var(--box);
  padding: 3px 9px; border-radius: 999px; border: 1px solid var(--line); }
#navbtns { position: fixed; right: 16px; bottom: 44px; display: flex; gap: 6px; z-index: 30; }
.cbtn { width: 34px; height: 34px; border-radius: 8px; border: 1px solid var(--line); background: var(--box);
  color: var(--ink); font-size: 16px; cursor: pointer; display: grid; place-items: center; }
.cbtn:hover { border-color: var(--accent); color: var(--accent); }
#toolbar { position: fixed; right: 16px; top: 12px; display: flex; gap: 6px; z-index: 30; }
#notes { position: fixed; left: 0; right: 0; bottom: 0; max-height: 42vh; overflow: auto; z-index: 45;
  background: var(--panel); border-top: 2px solid var(--accent); padding: 16px 22px 18px;
  transform: translateY(100%); transition: transform .25s ease; box-shadow: 0 -8px 30px rgba(0,0,0,.25); }
#notes.open { transform: translateY(0); }
#notes h4 { margin: 0 0 8px; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); }
#notes .ncontent { font-size: 15px; line-height: 1.5; color: var(--ink); max-width: 1000px; }
#notes .ncontent p { margin: 0; }
#help { position: fixed; inset: 0; z-index: 60; display: none; place-items: center; background: rgba(0,0,0,.35); }
#help.open { display: grid; }
#help .panel2 { background: var(--box); border: 1px solid var(--border-strong); border-radius: 14px;
  padding: 24px 28px; width: 440px; box-shadow: var(--shadow); color: var(--ink); }
#help h3 { margin: 0 0 14px; font-size: 20px; }
#help table { width: 100%; border-collapse: collapse; font-size: 15px; }
#help td { padding: 6px 4px; border-bottom: 1px solid var(--line); }
#help kbd { font-family: ui-monospace, monospace; background: var(--panel); border: 1px solid var(--line);
  border-radius: 5px; padding: 1px 7px; font-size: 13px; }
#help .close { margin-top: 16px; font-size: 13px; color: var(--ink-soft); }
@media (max-width: 700px) { #navbtns, #toolbar { display: none; } }
"""

SCRIPT = r"""
(function () {
  "use strict";
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var total = slides.length;
  var i = 0;
  var stage = document.getElementById("stage");
  var counter = document.getElementById("counter");
  var progbar = document.querySelector("#prog > i");
  var notes = document.getElementById("notes");
  var ncontent = notes.querySelector(".ncontent");
  var help = document.getElementById("help");

  function fromHash() { var n = parseInt((location.hash || "").replace("#", ""), 10); return (n >= 1 && n <= total) ? n - 1 : 0; }
  function render() {
    slides.forEach(function (s, n) { s.classList.toggle("active", n === i); });
    counter.textContent = (i + 1) + " / " + total;
    progbar.style.width = (i / (total - 1) * 100) + "%";
    if (notes.classList.contains("open")) updateNotes();
    if (location.hash !== "#" + (i + 1)) { try { history.replaceState(null, "", "#" + (i + 1)); } catch (e) { location.hash = i + 1; } }
  }
  function go(n) { i = Math.max(0, Math.min(total - 1, n)); render(); }
  function next() { go(i + 1); } function prev() { go(i - 1); }
  function updateNotes() { var src = slides[i].querySelector(".snotes"); ncontent.innerHTML = src ? src.innerHTML : "<p>(no notes)</p>"; }
  function toggleNotes() { notes.classList.toggle("open"); if (notes.classList.contains("open")) updateNotes(); }

  var THEME_KEY = "cgkm-strict-profiles-theme";
  function applyTheme(t) { var r = document.documentElement; if (t === "light" || t === "dark") r.setAttribute("data-theme", t); else r.removeAttribute("data-theme"); }
  function currentTheme() { var t = document.documentElement.getAttribute("data-theme"); if (t) return t; return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
  function toggleTheme() { var t = currentTheme() === "dark" ? "light" : "dark"; applyTheme(t); try { localStorage.setItem(THEME_KEY, t); } catch (e) {} }
  try { var saved = localStorage.getItem(THEME_KEY); if (saved) applyTheme(saved); } catch (e) {}

  function toggleFull() { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen && document.documentElement.requestFullscreen(); }

  function fit() { var pad = 24; stage.style.setProperty("--scale", Math.min((window.innerWidth - pad) / 1920, (window.innerHeight - pad) / 1080)); }
  window.addEventListener("resize", fit);

  document.getElementById("viewport").addEventListener("click", function (e) {
    if (e.target.closest("a, button")) return;
    if (help.classList.contains("open")) return;
    var x = e.clientX / window.innerWidth;
    if (x < 0.25) prev(); else if (x > 0.5) next();
  });

  document.addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "?" || (k === "/" && e.shiftKey)) { help.classList.toggle("open"); e.preventDefault(); return; }
    if (k === "Escape") { if (help.classList.contains("open")) help.classList.remove("open"); else if (notes.classList.contains("open")) notes.classList.remove("open"); return; }
    if (help.classList.contains("open")) return;
    switch (k) {
      case "ArrowRight": case " ": case "PageDown": case "j": next(); e.preventDefault(); break;
      case "ArrowLeft": case "PageUp": case "k": prev(); e.preventDefault(); break;
      case "Home": go(0); e.preventDefault(); break;
      case "End": go(total - 1); e.preventDefault(); break;
      case "s": case "S": case "n": case "N": toggleNotes(); break;
      case "t": case "T": toggleTheme(); break;
      case "f": case "F": toggleFull(); break;
    }
  });

  document.getElementById("prev").addEventListener("click", prev);
  document.getElementById("next").addEventListener("click", next);
  document.getElementById("btn-notes").addEventListener("click", toggleNotes);
  document.getElementById("btn-theme").addEventListener("click", toggleTheme);
  document.getElementById("btn-full").addEventListener("click", toggleFull);
  document.getElementById("btn-help").addEventListener("click", function () { help.classList.toggle("open"); });
  help.addEventListener("click", function (e) { if (e.target === help) help.classList.remove("open"); });
  window.addEventListener("hashchange", function () { var n = fromHash(); if (n !== i) go(n); });

  i = fromHash(); fit(); render();
})();
"""

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClinVar-GKM — {html.escape(title)}</title>
<style>
{css}
{VIEWER_CSS}
</style>
</head>
<body>
<div id="prog"><i></i></div>

<div id="viewport">
  <div id="stage">

{chr(10).join(slides)}

  </div>
</div>

<div id="counter">1 / {len(slides)}</div>
<div id="navbtns">
  <button class="cbtn" id="prev" title="Previous (←)" aria-label="Previous slide">‹</button>
  <button class="cbtn" id="next" title="Next (→)" aria-label="Next slide">›</button>
</div>
<div id="toolbar">
  <button class="cbtn" id="btn-notes" title="Speaker notes (S)" aria-label="Toggle speaker notes">✎</button>
  <button class="cbtn" id="btn-theme" title="Toggle theme (T)" aria-label="Toggle light/dark theme">◐</button>
  <button class="cbtn" id="btn-full" title="Fullscreen (F)" aria-label="Toggle fullscreen">⤢</button>
  <button class="cbtn" id="btn-help" title="Shortcuts (?)" aria-label="Show keyboard shortcuts">?</button>
</div>

<aside id="notes" aria-live="polite"><h4>Speaker notes</h4><div class="ncontent"></div></aside>

<div id="help" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
  <div class="panel2">
    <h3>Keyboard shortcuts</h3>
    <table>
      <tr><td><kbd>→</kbd> <kbd>Space</kbd></td><td>Next slide</td></tr>
      <tr><td><kbd>←</kbd></td><td>Previous slide</td></tr>
      <tr><td><kbd>Home</kbd> / <kbd>End</kbd></td><td>First / last slide</td></tr>
      <tr><td><kbd>S</kbd> or <kbd>N</kbd></td><td>Toggle speaker notes</td></tr>
      <tr><td><kbd>T</kbd></td><td>Toggle light / dark theme</td></tr>
      <tr><td><kbd>F</kbd></td><td>Toggle fullscreen</td></tr>
      <tr><td><kbd>?</kbd></td><td>Show / hide this help</td></tr>
    </table>
    <div class="close">An educational preview deck: it was not presented at an event.</div>
  </div>
</div>

<script>{SCRIPT}</script>
</body>
</html>
"""
open(out, "w").write(page)
print(f"wrote {out}: {len(slides)} slides, {len(page)} bytes")
