/* Shared R2 release browser. Each mount element:
     <div class="r2-browser" data-r2-type="TYPE"></div>
   TYPE ∈ latest | monthly | weekly | deltas | parquet-latest | previous | previous-summary
   (parquet-monthly is an alias of parquet-latest; Parquet is derived and one dataset is published)
   Reads the root version manifest (/index.json) and follows it to the index of the data line this docs
   version describes (ADR 0011): the page's docs version is the first segment of the site path ("1.1" in
   /1.1/data-access/download/, or /clinvar-gkm/1.1/... where the site is still under that prefix, ADR 0013),
   and the line is the root manifest's versions["1.1"]. A page
   without a version in its path (a local `zensical serve`), or a version with no data line, reads the
   current line. Then it renders each mount by its type.
   On a frozen line, a view whose files were deleted at the freeze (weekly fulls, Parquet) shows a note that
   links the same page in the latest docs. `previous` lists the frozen lines OLDER than this page's line
   (numerically lower: the 1.2 docs list 1.1 and 1.0, the 1.1 docs only 1.0), newest first, with their
   monthlies and deltas; `previous-summary` is a compact table of the same lines (schema, status,
   superseded_by, index/README/MANIFEST links) that links each to the Previous Releases page.
   Layout (ADR 0009, mirrors NCBI ClinVar): official monthlies at the line's top level, weekly/ (current
   month's weekly fulls), deltas/ (current month) + deltas/YYYY-MM/, archive/YYYY/ (+ deltas/YYYY-MM/),
   parquet/. Every link uses the `path` the index gives, so files that move at month or year rollover
   are always linked where they are now; folders are grouped from those paths.
   Overlaid onto older docs versions by src/scripts/build-versioned-docs.sh, so keep the mount types
   older pages use working.
   No-ops when no mount is present. CSP-safe (only same-host index fetches). */
(function () {
  var mounts = document.querySelectorAll(".r2-browser");
  if (!mounts.length) return;

  var BASE_URL = "https://data.clinvar-gkm.org";
  var ROOT_INDEX_URL = BASE_URL + "/index.json";   // root version manifest

  // Section order for composing Parquet URLs when the index entry carries no `sections` list.
  var PARQUET_SECTIONS = [
    "sequenceReference", "location", "allele", "copyNumberCount", "copyNumberChange",
    "gene", "variation", "condition", "conditionSet", "therapy", "therapyGroup", "submitter",
    "propositionPathogenicity", "propositionOncogenicity", "propositionSomaticClinicalImpact", "propositionClinvarCustom",
    "evidenceLine", "vcv_evidenceLine", "rcv_evidenceLine", "scv", "vcv", "rcv"
  ];

  var linePrefix = "";   // e.g. "v1/1.2/": the folder of the line's index.json

  // A docs page's site root, version and page: /1.2/data-access/download/ gives root "/", version "1.2" and
  // page "data-access/download/". The site may still be served under /clinvar-gkm/ (ADR 0013). Null for a
  // path without a version (a local `zensical serve`).
  function docsPath(path) {
    var m = /^(\/(?:clinvar-gkm\/)?)(\d+\.\d+)(?:\/(.*))?$/.exec(path || "");
    return m ? { root: m[1], version: m[2], page: m[3] || "" } : null;
  }
  // The docs version a page belongs to: "1.2" for /1.2/..., else null.
  function docsVersion(path) {
    var d = docsPath(path);
    return d ? d.version : null;
  }
  // The same page in the latest docs: an unversioned link, which the site's 404.html opens in the latest
  // release (or its home).
  function latestDocsHref(path) {
    var d = docsPath(path);
    return location.origin + (d ? d.root + d.page : "/");
  }

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else if (k === "className") e.className = attrs[k];
      else if (k === "style") Object.assign(e.style, attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    if (children) children.forEach(function (c) {
      if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return e;
  }

  function formatSize(bytes) {
    if (!bytes) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB";
    return (bytes / 1073741824).toFixed(2) + " GB";
  }

  function url(path) { return BASE_URL + "/" + String(path).replace(/^\//, ""); }
  function baseName(path) { return String(path).replace(/\/$/, "").split("/").pop(); }
  function dirOf(path) { var p = String(path).replace(/^\//, ""); return p.slice(0, p.lastIndexOf("/") + 1); }
  // Folder label relative to the line folder ("weekly/", "deltas/2026-09/"); the line folder itself shows as-is.
  function relDir(dir, prefix) {
    prefix = prefix === undefined ? linePrefix : prefix;
    if (prefix && dir.indexOf(prefix) === 0) return dir.slice(prefix.length) || prefix;
    return dir;
  }

  function meta(text) { return el("span", { className: "r2-size", text: text }); }
  function dateBadge(modified) {       // returns null when absent (graceful fallback)
    return modified ? el("span", { className: "r2-date", text: modified }) : null;
  }
  function fileRow(name, href, size, modified) {
    return el("div", { className: "r2-file" }, [
      el("a", { href: href, text: name }),
      size ? meta(formatSize(size)) : null,
      dateBadge(modified)
    ]);
  }
  function folder(label, open, badge) {
    var f = el("details", { className: "r2-folder" });
    if (open) f.setAttribute("open", "");
    var s = el("summary", { text: label });
    if (badge) s.appendChild(badge);
    f.appendChild(s);
    return f;
  }
  function note(title, children) {
    return el("div", { className: "admonition note" }, [
      el("p", { className: "admonition-title", text: title }),
      el("p", {}, children)
    ]);
  }

  // --- index accessors (tolerant of the pre-ADR-0009 index shape) -----------
  function archiveLists(data, key) {
    var arch = data.archives || {}, out = [];
    Object.keys(arch).forEach(function (y) { out = out.concat((arch[y] && arch[y][key]) || []); });
    return out;
  }
  function monthlies(data) { return ((data.datasets && data.datasets.monthly) || []).concat(archiveLists(data, "monthly")); }
  function weeklies(data) { return (data.datasets && data.datasets.weekly) || data.weekly || []; }
  function deltas(data) {
    return (data.deltas || []).concat(archiveLists(data, "deltas"))
      .filter(function (d) { return d.release && d.release !== "latest"; });
  }
  function parquetEntry(data) {
    var p = (data.datasets && data.datasets.parquet) || data.parquet;
    if (Array.isArray(p)) return p.filter(function (x) { return x.latest; })[0] || p[0] || null;
    return p || null;
  }
  function deltaBundlePath(d) {
    if (d.bundle && d.bundle.path) return d.bundle.path;
    if (/\.json\.gz$/.test(d.path || "")) return d.path;
    var dir = baseName(d.path || "");                 // pre-ADR-0009: deltas/<YYYY-MMDD>/
    return String(d.path).replace(/\/?$/, "/") + "clinvar-gkm-delta_" + dir + ".json.gz";
  }
  function isPointer(f) { return f.latest || /00-latest/.test(f.name || f.path || ""); }
  function key(f) { return String(f.source_release || f.release || f.name || f.path); }
  function newestDated(list) {
    var dated = list.filter(function (x) { return !isPointer(x); });
    dated.sort(function (a, b) { return key(b).localeCompare(key(a)); });
    return dated[0] || null;
  }
  function pointer(list) { return list.filter(isPointer)[0] || null; }
  // The Parquet entry has no `modified`; its build_date (ISO timestamp, from parquet/manifest.json) stands in.
  function parquetDate(p) { return p && (p.modified || (p.build_date ? String(p.build_date).slice(0, 10) : null)); }
  function label(name) { return String(name).replace(/^clinvar-gkm(-delta)?_|\.json\.gz$/g, ""); }

  // Group entries into folders by the directory of pathOf(entry); the line folder first, then newest first.
  function byFolder(list, pathOf, prefix) {
    var groups = {};
    list.forEach(function (f) { var d = dirOf(pathOf(f)); (groups[d] = groups[d] || []).push(f); });
    var dirs = Object.keys(groups).sort(function (a, b) {
      var ra = relDir(a, prefix), rb = relDir(b, prefix);
      var ta = ra.indexOf("archive/") === 0, tb = rb.indexOf("archive/") === 0;
      if (ta !== tb) return ta ? 1 : -1;          // archive/ last
      if (a.length !== b.length) return a.length - b.length;   // shallower first (current month, line top)
      return b.localeCompare(a);                  // newest first
    });
    return dirs.map(function (d) { return { dir: d, items: groups[d] }; });
  }

  // --- frozen lines -----------------------------------------------------------
  // ctx (see loadContext): the line this page reads, whether it is frozen, and when it was frozen.
  function lineName(ctx) { return (ctx.entry && ctx.entry.line ? ctx.entry.line : linePrefix.replace(/\/$/, "")) + "/"; }
  // what: what was deleted, e.g. "weekly full bundles"; plural picks "were" or "was".
  function removedNote(ctx, what, plural) {
    return note("Removed when the line was frozen", [
      "The " + what + " of " + lineName(ctx) + (plural ? " were" : " was") +
        " removed when the line was frozen" + (ctx.frozenAt ? " on " + ctx.frozenAt : "") +
        ". A frozen line keeps its monthlies and deltas, unchanged; its weekly fulls and Parquet set are deleted. " +
        "For current data, see ",
      el("a", { href: latestDocsHref(location.pathname), text: "the latest docs" }),
      "."
    ]);
  }

  // --- view renderers -------------------------------------------------------
  function renderLatest(mount, data, ctx) {
    var m = monthlies(data), w = weeklies(data), ds = deltas(data), p = parquetEntry(data);
    var mPtr = pointer(m), mDated = newestDated(m);
    var wPtr = pointer(w), wDated = newestDated(w);
    var dNew = newestDated(ds);
    var dropParquet = ctx.frozen && !p;

    // "Get" cells link stable 00-latest pointers where they exist. The Parquet dataset is a folder (no
    // single file), so link to the Parquet page; "../parquet/" is page-relative from the hub
    // (/data-access/download/ -> /data-access/parquet/).
    var monthlyGet = (mPtr || mDated) ? [el("a", { href: url((mPtr || mDated).path), text: "bundle" })] : [];
    var weeklyGet = (wPtr || wDated) ? [el("a", { href: url((wPtr || wDated).path), text: "bundle" })] : [];
    var deltaGet = dNew ? [
      el("a", { href: url(deltaBundlePath(dNew)), text: "bundle" }),
      el("span", { text: " · " }),
      el("a", { href: url(dNew.manifest), text: "manifest" })
    ] : [];
    var parquetGet = [el("a", { href: "../parquet/", text: "browse →" })];

    var rows = [
      ["Official monthly", mDated ? label(mDated.name || baseName(mDated.path)) +
        (mDated.source_release ? " (from " + mDated.source_release + ")" : "") : "", mDated && mDated.modified, monthlyGet],
      ["Weekly full", wDated ? label(wDated.name || baseName(wDated.path)).replace(/^(\d{4})-(\d{2})(\d{2})$/, "$1-$2-$3") : "",
       wDated && wDated.modified, weeklyGet],
      ["Weekly delta", dNew ? dNew.release : "", dNew && dNew.modified, deltaGet],
      ["Parquet (derived)", p ? (p.source_release ? "built from " + p.source_release : "latest") : "",
       parquetDate(p), parquetGet]
    ].filter(function (r) {
      return (r[0] !== "Weekly full" || w.length) && (r[0] !== "Parquet (derived)" || !dropParquet);
    });

    var table = el("table", { className: "r2-latest" });
    table.appendChild(el("thead", {}, [el("tr", {}, ["Type", "Release", "R2 available", "Get"].map(
      function (h) { return el("th", { text: h }); }))]));
    var tbody = el("tbody");
    rows.forEach(function (r) {
      tbody.appendChild(el("tr", {}, [
        el("td", { text: r[0] }), el("td", { text: r[1] }), el("td", { text: r[2] || "" }), el("td", {}, r[3])
      ]));
    });
    table.appendChild(tbody);
    mount.appendChild(table);

    if (ctx.frozen && (!w.length || !p)) {
      mount.appendChild(!w.length && !p ? removedNote(ctx, "weekly full bundles and the Parquet set", true)
        : !w.length ? removedNote(ctx, "weekly full bundles", true) : removedNote(ctx, "Parquet set", false));
    }
  }

  function renderFiles(mount, files, emptyText, prefix) {
    if (!files.length) { mount.appendChild(el("div", { className: "r2-file", text: emptyText })); return; }
    byFolder(files, function (f) { return f.path; }, prefix).forEach(function (g, i) {
      var f = folder(relDir(g.dir, prefix), i === 0);
      g.items.slice().sort(function (a, b) {
        if (isPointer(a) !== isPointer(b)) return isPointer(a) ? -1 : 1;
        return key(b).localeCompare(key(a));
      }).forEach(function (x) {
        f.appendChild(fileRow(x.name || baseName(x.path), url(x.path), x.size, x.modified));
      });
      mount.appendChild(f);
    });
  }

  // Deltas by year, not by bucket folder: the current year (the newest delta's year) open, then an
  // "Archived years" group with one collapsible list per earlier year. Newest first everywhere; links use
  // each file's own path, so month and year rollovers never break them.
  function deltaRow(d) {
    var size = d.bundle && d.bundle.size, path = deltaBundlePath(d);
    return el("div", { className: "r2-file" }, [
      el("a", { href: url(path), text: baseName(path) }),
      size ? meta(formatSize(size)) : null,
      d.manifest ? el("span", { className: "r2-size" }, [el("a", { href: url(d.manifest), text: "manifest" })]) : null,
      dateBadge(d.modified)
    ]);
  }
  function count(n) { return meta(n + (n === 1 ? " delta" : " deltas")); }
  function newestRelease(a, b) { return b.release.localeCompare(a.release); }

  function renderDeltas(mount, list) {
    if (!list.length) { mount.appendChild(el("div", { className: "r2-file", text: "No weekly deltas listed yet." })); return; }
    var years = {};
    list.forEach(function (d) { var y = String(d.release).slice(0, 4); (years[y] = years[y] || []).push(d); });
    var order = Object.keys(years).sort().reverse(), current = order[0];

    var cur = folder(current + " (current year)", true, count(years[current].length));
    years[current].slice().sort(newestRelease).forEach(function (d) { cur.appendChild(deltaRow(d)); });
    mount.appendChild(cur);

    var past = order.slice(1);
    var arch = folder("Archived years", false,
      meta(past.length ? past.length + (past.length === 1 ? " year" : " years") : "none yet"));
    if (!past.length) {
      arch.appendChild(el("div", { className: "r2-file",
        text: "None yet. When the first release of a new year is published, the previous year's deltas move to archive/YYYY/deltas/." }));
    }
    past.forEach(function (y) {
      var f = folder(y, false, count(years[y].length));
      f.className += " r2-year";
      years[y].slice().sort(newestRelease).forEach(function (d) { f.appendChild(deltaRow(d)); });
      arch.appendChild(f);
    });
    mount.appendChild(arch);
  }

  // The one published Parquet dataset: derived from the bundle and overwritten every release.
  function renderParquetLatest(mount, p, ctx) {
    if (!p) {
      if (ctx.frozen) mount.appendChild(removedNote(ctx, "Parquet set", false));
      return;
    }
    var dir = String(p.path).replace(/^\//, "").replace(/\/?$/, "/");
    var title = relDir(dir) + (p.source_release ? " (built from " + p.source_release + ")" : "");
    var f = folder(title, true, dateBadge(parquetDate(p)));
    var manifest = p.manifest || (/00-latest/.test(dir) ? null : dir + "manifest.json");
    if (manifest) f.appendChild(fileRow(baseName(manifest), url(manifest)));
    // Fallback when the index lists no sections: the 1.1 (BigQuery) set has 22 tables, the 2.0 set 20
    // (one evidenceLine table, no vcv_evidenceLine / rcv_evidenceLine).
    var fallback = /^BigQuery/.test(p.builder || "") ? PARQUET_SECTIONS : PARQUET_SECTIONS.filter(function (s) {
      return s !== "vcv_evidenceLine" && s !== "rcv_evidenceLine";
    });
    (p.sections && p.sections.length ? p.sections : fallback).forEach(function (s) {
      f.appendChild(fileRow(s + ".parquet", url(dir + s + ".parquet")));
    });
    mount.appendChild(f);
  }

  function renderWeekly(mount, data, ctx) {
    var w = weeklies(data);
    if (!w.length && ctx.frozen) mount.appendChild(removedNote(ctx, "weekly full bundles", true));
    else renderFiles(mount, w, "No weekly full bundles listed yet.");
  }

  // --- previous releases: every frozen line ----------------------------------
  function lineOrder(a, b) {          // newest line first: by major, then minor
    var pa = a.split(".").map(Number), pb = b.split(".").map(Number);
    return (pb[0] - pa[0]) || (pb[1] - pa[1]);
  }
  function frozenDate(manifest) {
    return manifest && manifest.frozen_at ? String(manifest.frozen_at).slice(0, 10) : null;
  }

  // The frozen lines older than the page's line (ctx.key), newest first. Never the page's own line or a newer
  // one: each docs version lists only what came before it.
  function olderFrozen(root, ctx) {
    var versions = root.versions || {};
    return Object.keys(versions).filter(function (k) {
      return versions[k] && versions[k].status === "frozen" && /^\d+\.\d+$/.test(k) &&
        (!ctx.key || lineOrder(k, ctx.key) > 0);
    }).sort(lineOrder);
  }
  function noneBefore(mount, ctx) {
    mount.appendChild(el("div", { className: "r2-file", text: ctx.key
      ? "There are no release lines before " + lineName(ctx) + "."
      : "No release line has been frozen yet." }));
  }
  // index.json, feed.xml, and README.txt + MANIFEST.json once the freeze has written them.
  function lineLinks(entry, prefix, manifest) {
    var links = [["index.json", entry.index], ["feed.xml", entry.feed]];
    if (manifest) links.push(["README.txt", prefix + "README.txt"], ["MANIFEST.json", prefix + "MANIFEST.json"]);
    var row = el("div", { className: "r2-file" });
    links.filter(function (l) { return l[1]; }).forEach(function (l, i) {
      if (i) row.appendChild(el("span", { text: " · " }));
      row.appendChild(el("a", { href: url(l[1]), text: l[0] }));
    });
    return row;
  }
  function lineAnchor(k) { return "line-" + k.replace(".", "-"); }

  function renderPrevious(mount, root, ctx) {
    var versions = root.versions || {};
    var frozen = olderFrozen(root, ctx);
    if (!frozen.length) { noneBefore(mount, ctx); return; }
    frozen.forEach(function (k) {
      var entry = versions[k];
      var line = String(entry.line || "").replace(/\/?$/, "/");
      var section = el("div", { className: "r2-line" });
      section.appendChild(el("h3", { id: lineAnchor(k),
        text: line + (entry.schema ? " (schema " + entry.schema + ")" : "") }));
      mount.appendChild(section);
      if (!entry.index) { section.appendChild(el("div", { className: "r2-error", text: "No index for this line." })); return; }
      var prefix = dirOf(entry.index.replace(/^\//, ""));
      Promise.all([
        fetchJSON(url(entry.index)),
        fetchJSON(url(prefix + "MANIFEST.json")).catch(function () { return null; })
      ]).then(function (got) {
        renderFrozenLine(section, entry, prefix, got[0], got[1]);
      }).catch(function (err) {
        section.appendChild(el("div", { className: "r2-error",
          text: "Unable to load " + url(entry.index) + " (" + err.message + ")." }));
      });
    });
  }

  function renderFrozenLine(section, entry, prefix, data, manifest) {
    var facts = [];
    if (entry.superseded_by) facts.push("Superseded by " + String(entry.superseded_by).replace(/\/?$/, "/") + ".");
    var when = frozenDate(manifest);
    facts.push(when ? "Frozen on " + when + "." : "Frozen.");
    if (data.latest_release) facts.push("Last release: " + data.latest_release + ".");
    section.appendChild(el("p", { text: facts.join(" ") }));

    section.appendChild(lineLinks(entry, prefix, manifest));

    var m = monthlies(data);
    var mf = folder("Monthly full bundles", false, meta(m.filter(function (x) { return !isPointer(x); }).length + " monthlies"));
    renderFiles(mf, m, "No monthly full bundles listed.", prefix);
    section.appendChild(mf);

    var ds = deltas(data);
    var df = folder("Weekly deltas", false, count(ds.length));
    if (!ds.length) df.appendChild(el("div", { className: "r2-file", text: "No weekly deltas listed." }));
    byFolder(ds, deltaBundlePath, prefix).forEach(function (g) {
      var f = folder(relDir(g.dir, prefix), false, count(g.items.length));
      f.className += " r2-year";
      g.items.slice().sort(newestRelease).forEach(function (d) { f.appendChild(deltaRow(d)); });
      df.appendChild(f);
    });
    section.appendChild(df);
  }

  // Compact table of the same lines for the Get the Data landing page; "../previous-releases/" is
  // page-relative from the hub (/data-access/download/ -> /data-access/previous-releases/).
  function renderPreviousSummary(mount, root, ctx) {
    var versions = root.versions || {};
    var frozen = olderFrozen(root, ctx);
    if (!frozen.length) { noneBefore(mount, ctx); return; }
    var table = el("table", { className: "r2-latest" });
    table.appendChild(el("thead", {}, [el("tr", {}, ["Line", "Schema", "Status", "Files", "Monthlies and deltas"].map(
      function (h) { return el("th", { text: h }); }))]));
    var tbody = el("tbody");
    frozen.forEach(function (k) {
      var entry = versions[k];
      var status = el("td", { text: "frozen" + (entry.superseded_by
        ? ", superseded by " + String(entry.superseded_by).replace(/\/?$/, "/") : "") });
      var files = el("td", {});
      tbody.appendChild(el("tr", {}, [
        el("td", { text: String(entry.line || k).replace(/\/?$/, "/") }),
        el("td", { text: entry.schema || "" }),
        status,
        files,
        el("td", {}, [el("a", { href: "../previous-releases/#" + lineAnchor(k), text: "Previous Releases →" })])
      ]));
      if (!entry.index) return;
      var prefix = dirOf(entry.index.replace(/^\//, ""));
      fetchJSON(url(prefix + "MANIFEST.json")).catch(function () { return null; }).then(function (mf) {
        var when = frozenDate(mf);
        if (when) status.textContent = status.textContent.replace(/^frozen/, "frozen " + when);
        files.appendChild(lineLinks(entry, prefix, mf));
      });
    });
    table.appendChild(tbody);
    mount.appendChild(table);
  }

  function render(mount, data, root, ctx) {
    var t = mount.getAttribute("data-r2-type");
    if (t === "previous") renderPrevious(mount, root, ctx);
    else if (t === "previous-summary") renderPreviousSummary(mount, root, ctx);
    else if (t === "latest") renderLatest(mount, data, ctx);
    else if (t === "monthly") renderFiles(mount, monthlies(data), "No monthly full bundles listed.");
    else if (t === "weekly") renderWeekly(mount, data, ctx);
    else if (t === "deltas") renderDeltas(mount, deltas(data));
    else if (t === "parquet-latest" || t === "parquet-monthly") renderParquetLatest(mount, parquetEntry(data), ctx);
  }

  function fail(msg) {
    mounts.forEach(function (m) {
      m.appendChild(el("div", { className: "r2-error", text: msg }));
    });
  }

  function fetchJSON(u) {
    return fetch(u).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  // The current line's key in the root manifest: the line marked status "current", else the highest
  // active (then any) key. Returns null when the manifest lists no lines.
  function currentKey(root) {
    var versions = root.versions || {};
    var keys = Object.keys(versions);
    if (!keys.length) return null;
    var current = keys.filter(function (k) { return versions[k].status === "current"; });
    var pool = current.length ? current
             : (root.active && root.active.length ? root.active.slice() : keys);
    pool.sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
    return pool[pool.length - 1];
  }

  // The data line this page reads: the line of its docs version when the root manifest has one, else the
  // current line.
  function pickLine(root, version) {
    var versions = root.versions || {};
    var cur = currentKey(root);
    var k = version && versions[version] ? version : cur;
    return { key: k, currentKey: cur, entry: k ? versions[k] : null };
  }

  // Load the root manifest, the line index of this page's data line, and, for a frozen line, the date in its
  // MANIFEST.json. If the root doc is itself a full index (pre-/v1 flat layout), use it directly.
  function loadContext() {
    var needLine = Array.prototype.some.call(mounts, function (m) {
      return !/^previous(-summary)?$/.test(m.getAttribute("data-r2-type"));
    });
    return fetchJSON(ROOT_INDEX_URL).then(function (root) {
      if (root.datasets || root.deltas) return { root: root, data: root, ctx: { frozen: false } };
      var ctx = pickLine(root, docsVersion(location.pathname));
      var rel = ctx.entry && ctx.entry.index;
      if (!rel) throw new Error("no active version in root manifest");
      rel = rel.replace(/^\//, "");
      linePrefix = dirOf(rel);
      if (!needLine) return { root: root, data: {}, ctx: ctx };
      return fetchJSON(url(rel)).then(function (data) {
        ctx.frozen = ctx.entry.status === "frozen" || data.status === "frozen";
        if (!ctx.frozen) return { root: root, data: data, ctx: ctx };
        return fetchJSON(url(linePrefix + "MANIFEST.json"))
          .then(function (mf) { ctx.frozenAt = frozenDate(mf); }, function () {})
          .then(function () { return { root: root, data: data, ctx: ctx }; });
      });
    });
  }

  loadContext()
    .then(function (got) { mounts.forEach(function (m) { render(m, got.data, got.root, got.ctx); }); })
    .catch(function (err) {
      var isNetwork = (err instanceof TypeError) ||
        /failed to fetch|networkerror|load failed/i.test(err.message || "");
      fail(isNetwork
        ? "Couldn't load the release index (network/CORS). Fetch it directly: curl -s " + ROOT_INDEX_URL
        : "Unable to load the release index (" + err.message + ").");
    });
})();
