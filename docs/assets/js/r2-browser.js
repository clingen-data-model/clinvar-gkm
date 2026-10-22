/* Shared R2 release browser. Each mount element:
     <div class="r2-browser" data-r2-type="TYPE"></div>
   TYPE ∈ latest | monthly | weekly | deltas | parquet-latest
   (parquet-monthly is an alias of parquet-latest; Parquet is derived and one dataset is published)
   Reads the root version manifest (/index.json), follows it to the current line's index
   (e.g. /v1/1.1/index.json), then renders each mount by its type.
   Layout (ADR 0009, mirrors NCBI ClinVar): official monthlies at the line's top level, weekly/ (current
   month's weekly fulls), deltas/ (current month) + deltas/YYYY-MM/, archive/YYYY/ (+ deltas/YYYY-MM/),
   parquet/. Every link uses the `path` the index gives, so files that move at month or year rollover
   are always linked where they are now; folders are grouped from those paths.
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

  var linePrefix = "";   // e.g. "v1/1.1/": the folder of the current line's index.json

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else if (k === "className") e.className = attrs[k];
      else if (k === "style") Object.assign(e.style, attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    if (children) children.forEach(function (c) { if (c) e.appendChild(c); });
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
  function relDir(dir) {
    if (linePrefix && dir.indexOf(linePrefix) === 0) return dir.slice(linePrefix.length) || linePrefix;
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
  function byFolder(list, pathOf) {
    var groups = {};
    list.forEach(function (f) { var d = dirOf(pathOf(f)); (groups[d] = groups[d] || []).push(f); });
    var dirs = Object.keys(groups).sort(function (a, b) {
      var ra = relDir(a), rb = relDir(b);
      var ta = ra.indexOf("archive/") === 0, tb = rb.indexOf("archive/") === 0;
      if (ta !== tb) return ta ? 1 : -1;          // archive/ last
      if (a.length !== b.length) return a.length - b.length;   // shallower first (current month, line top)
      return b.localeCompare(a);                  // newest first
    });
    return dirs.map(function (d) { return { dir: d, items: groups[d] }; });
  }

  // --- view renderers -------------------------------------------------------
  function renderLatest(mount, data) {
    var m = monthlies(data), w = weeklies(data), ds = deltas(data), p = parquetEntry(data);
    var mPtr = pointer(m), mDated = newestDated(m);
    var wPtr = pointer(w), wDated = newestDated(w);
    var dNew = newestDated(ds);

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
    ].filter(function (r) { return r[0] !== "Weekly full" || w.length; });

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
  }

  function renderFiles(mount, files, emptyText) {
    if (!files.length) { mount.appendChild(el("div", { className: "r2-file", text: emptyText })); return; }
    byFolder(files, function (f) { return f.path; }).forEach(function (g, i) {
      var f = folder(relDir(g.dir), i === 0);
      g.items.slice().sort(function (a, b) {
        if (isPointer(a) !== isPointer(b)) return isPointer(a) ? -1 : 1;
        return key(b).localeCompare(key(a));
      }).forEach(function (x) {
        f.appendChild(fileRow(x.name || baseName(x.path), url(x.path), x.size, x.modified));
      });
      mount.appendChild(f);
    });
  }

  function renderDeltas(mount, list) {
    byFolder(list, deltaBundlePath).forEach(function (g, i) {
      var f = folder(relDir(g.dir), i === 0);
      g.items.slice().sort(function (a, b) { return b.release.localeCompare(a.release); }).forEach(function (d) {
        var size = d.bundle && d.bundle.size;
        f.appendChild(el("div", { className: "r2-file" }, [
          el("a", { href: url(deltaBundlePath(d)), text: d.release }),
          size ? meta(formatSize(size)) : null,
          d.manifest ? el("span", { className: "r2-size" }, [el("a", { href: url(d.manifest), text: "manifest" })]) : null,
          dateBadge(d.modified)
        ]));
      });
      mount.appendChild(f);
    });
  }

  // The one published Parquet dataset: derived from the bundle and overwritten every release.
  function renderParquetLatest(mount, p) {
    if (!p) return;
    var dir = String(p.path).replace(/^\//, "").replace(/\/?$/, "/");
    var title = relDir(dir) + (p.source_release ? " (built from " + p.source_release + ")" : "");
    var f = folder(title, true, dateBadge(parquetDate(p)));
    var manifest = p.manifest || (/00-latest/.test(dir) ? null : dir + "manifest.json");
    if (manifest) f.appendChild(fileRow(baseName(manifest), url(manifest)));
    (p.sections && p.sections.length ? p.sections : PARQUET_SECTIONS).forEach(function (s) {
      f.appendChild(fileRow(s + ".parquet", url(dir + s + ".parquet")));
    });
    mount.appendChild(f);
  }

  function render(mount, data) {
    var t = mount.getAttribute("data-r2-type");
    if (t === "latest") renderLatest(mount, data);
    else if (t === "monthly") renderFiles(mount, monthlies(data), "No monthly full bundles listed.");
    else if (t === "weekly") renderFiles(mount, weeklies(data), "No weekly full bundles listed yet.");
    else if (t === "deltas") renderDeltas(mount, deltas(data));
    else if (t === "parquet-latest" || t === "parquet-monthly") renderParquetLatest(mount, parquetEntry(data));
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

  // Resolve the current line from the root manifest: prefer the line marked status "current", else the
  // highest active (then any) key. Returns its index path (e.g. "v1/1.1/index.json"), or null.
  function versionIndexPath(root) {
    var versions = root.versions || {};
    var keys = Object.keys(versions);
    if (!keys.length) return null;
    var current = keys.filter(function (k) { return versions[k].status === "current"; });
    var pool = current.length ? current
             : (root.active && root.active.length ? root.active.slice() : keys);
    pool.sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
    var chosen = versions[pool[pool.length - 1]];
    return (chosen && chosen.index) ? chosen.index : null;
  }

  // Load the release index. The root /index.json is a thin version manifest; follow it to the current
  // line's index. If the root doc is itself a full index (pre-/v1 flat layout), use it directly.
  function loadIndex() {
    return fetchJSON(ROOT_INDEX_URL).then(function (root) {
      if (root.datasets || root.deltas) return root;      // full index served at root
      var rel = versionIndexPath(root);
      if (!rel) throw new Error("no active version in root manifest");
      rel = rel.replace(/^\//, "");
      linePrefix = dirOf(rel);
      return fetchJSON(url(rel));
    });
  }

  loadIndex()
    .then(function (data) { mounts.forEach(function (m) { render(m, data); }); })
    .catch(function (err) {
      var isNetwork = (err instanceof TypeError) ||
        /failed to fetch|networkerror|load failed/i.test(err.message || "");
      fail(isNetwork
        ? "Couldn't load the release index (network/CORS). Fetch it directly: curl -s " + ROOT_INDEX_URL
        : "Unable to load the release index (" + err.message + ").");
    });
})();
