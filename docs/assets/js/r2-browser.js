/* Shared R2 release browser. Each mount element:
     <div class="r2-browser" data-r2-type="TYPE"></div>
   TYPE ∈ latest | monthly | deltas | parquet-monthly | parquet-weekly
   Fetches index.json once per page; renders each mount by its type.
   No-ops when no mount is present. CSP-safe (no external requests besides index.json). */
(function () {
  var mounts = document.querySelectorAll(".r2-browser");
  if (!mounts.length) return;

  var BASE_URL = "https://pub-f0ad0e0dac0345408dcc95bda20beb42.r2.dev";
  var INDEX_URL = BASE_URL + "/index.json";

  // Stable section order for composing Parquet URLs (full sets always carry all 22).
  var PARQUET_SECTIONS = [
    "sequenceReference", "location", "allele", "copyNumberCount", "copyNumberChange",
    "gene", "variation", "condition", "conditionSet", "therapy", "therapyGroup", "submitter",
    "varcond-proposition", "vartumor-proposition", "vartherapy-proposition", "varcustom-proposition",
    "evidenceLine", "vcv_evidenceLine", "rcv_evidenceLine", "scv", "vcv", "rcv"
  ];
  var LATEST_MONTHLY = "clinvar-gkm_00-latest.json.gz";

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

  function meta(text) { return el("span", { className: "r2-size", text: text }); }
  function dateBadge(modified) {       // returns null when absent (graceful fallback)
    return modified ? el("span", { className: "r2-date", text: modified }) : null;
  }
  function fileRow(name, url, size, modified) {
    return el("div", { className: "r2-file" }, [
      el("a", { href: url, text: name }),
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

  // --- view renderers -------------------------------------------------------
  function newestDated(list) {          // newest entry whose release != "latest"
    var dated = list.filter(function (x) {
      return (x.release && x.release !== "latest") ||
             (x.name && x.name !== LATEST_MONTHLY);
    });
    dated.sort(function (a, b) {
      return String(b.release || b.name).localeCompare(String(a.release || a.name));
    });
    return dated[0] || null;
  }

  function renderLatest(mount, data) {
    var monthly = (data.datasets && data.datasets.monthly) || [];
    var parquet = (data.datasets && data.datasets.parquet) || [];
    var deltas = data.deltas || [];
    var mLatest = monthly.filter(function (f) { return f.latest; })[0];
    var dLatest = deltas.filter(function (d) { return d.latest; })[0];
    var mDated = newestDated(monthly), dDated = newestDated(deltas), pDated = newestDated(parquet);

    function deltaDir(d) { return d.path.replace(/^deltas\//, "").replace(/\/$/, ""); }

    // "Get" cells: monthly = one stable bundle; delta = bundle + manifest; parquet set is a
    // directory (no single file) so link to the Parquet page. "../parquet/" is page-relative
    // from the hub (/data-access/download/ -> /data-access/parquet/); verified in the serve test.
    var monthlyGet = mLatest ? [el("a", { href: BASE_URL + "/" + mLatest.path, text: "bundle" })] : [];
    var deltaGet = dLatest ? [
      el("a", { href: BASE_URL + "/" + dLatest.path + "clinvar-gkm-delta_00-latest.json.gz", text: "bundle" }),
      el("span", { text: " · " }),
      el("a", { href: BASE_URL + "/" + dLatest.path + "manifest.json", text: "manifest" })
    ] : [];
    var parquetGet = [el("a", { href: "../parquet/", text: "browse sets →" })];

    var rows = [
      ["Monthly full", mDated ? mDated.name.replace(/^clinvar-gkm_|\.json\.gz$/g, "") : "", mDated && mDated.modified, monthlyGet],
      ["Weekly delta", dDated ? deltaDir(dDated).replace(/^(\d{4})-(\d{2})(\d{2})$/, "$1-$2-$3") : "", dDated && dDated.modified, deltaGet],
      ["Parquet (full)", pDated ? pDated.release : "", pDated && pDated.modified, parquetGet]
    ];

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

  function renderFileList(mount, files, archivesByYear) {
    var top = folder("datasets/", true);
    (files || []).forEach(function (f) {
      top.appendChild(fileRow(f.name, BASE_URL + "/" + f.path, f.size, f.modified));
    });
    mount.appendChild(top);
    var years = Object.keys(archivesByYear || {}).sort().reverse();
    years.forEach(function (y, i) {
      var yf = folder("archives/" + y + "/", i === 0);
      (archivesByYear[y].monthly || []).forEach(function (f) {
        yf.appendChild(fileRow(f.name, BASE_URL + "/" + f.path, f.size, f.modified));
      });
      mount.appendChild(yf);
    });
  }

  function renderDeltas(mount, deltas) {
    var top = folder("deltas/", true);
    (deltas || []).slice().sort(function (a, b) {
      if (a.release === "latest") return -1;
      if (b.release === "latest") return 1;
      return b.release.localeCompare(a.release);
    }).forEach(function (d) {
      var dir = d.path.replace(/^deltas\//, "").replace(/\/$/, "");
      var row = el("div", { className: "r2-file" }, [
        el("a", { href: BASE_URL + "/" + d.path + "clinvar-gkm-delta_" + dir + ".json.gz", text: dir }),
        el("span", { className: "r2-size" }, [el("a", { href: BASE_URL + "/" + d.manifest, text: "manifest.json" })]),
        dateBadge(d.modified)
      ]);
      top.appendChild(row);
    });
    mount.appendChild(top);
  }

  function renderParquetMonthly(mount, sets, archivesByYear) {
    function set(p, open) {
      var label = p.release === "latest" ? "00-latest" : p.release;
      var f = folder(label, open, dateBadge(p.modified));
      PARQUET_SECTIONS.forEach(function (s) {
        f.appendChild(fileRow(s + ".parquet", BASE_URL + "/" + p.path + s + ".parquet"));
      });
      return f;
    }
    (sets || []).slice().sort(function (a, b) {
      if (a.release === "latest") return -1;
      if (b.release === "latest") return 1;
      return b.release.localeCompare(a.release);
    }).forEach(function (p, i) { mount.appendChild(set(p, i === 0)); });
    var years = Object.keys(archivesByYear || {}).sort().reverse();
    years.forEach(function (y) {
      (archivesByYear[y].parquet || []).forEach(function (p) { mount.appendChild(set(p, false)); });
    });
  }

  function renderParquetWeekly(mount, deltas) {
    (deltas || []).filter(function (d) { return d.release !== "latest" && d.parquet && d.parquet.length; })
      .sort(function (a, b) { return b.release.localeCompare(a.release); })
      .forEach(function (d, i) {
        var f = folder(d.release, i === 0, dateBadge(d.modified));
        d.parquet.forEach(function (s) {
          f.appendChild(fileRow(s + ".parquet", BASE_URL + "/" + d.path + "parquet/" + s + ".parquet"));
        });
        mount.appendChild(f);
      });
  }

  function render(mount, data) {
    var t = mount.getAttribute("data-r2-type");
    var arch = data.archives || {};
    if (t === "latest") renderLatest(mount, data);
    else if (t === "monthly") renderFileList(mount, (data.datasets || {}).monthly, arch);
    else if (t === "deltas") renderDeltas(mount, data.deltas);
    else if (t === "parquet-monthly") renderParquetMonthly(mount, (data.datasets || {}).parquet, arch);
    else if (t === "parquet-weekly") renderParquetWeekly(mount, data.deltas);
  }

  function fail(msg) {
    mounts.forEach(function (m) {
      m.appendChild(el("div", { className: "r2-error", text: msg }));
    });
  }

  fetch(INDEX_URL)
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (data) { mounts.forEach(function (m) { render(m, data); }); })
    .catch(function (err) {
      var isNetwork = (err instanceof TypeError) ||
        /failed to fetch|networkerror|load failed/i.test(err.message || "");
      fail(isNetwork
        ? "Couldn't load the release index (network/CORS). Fetch it directly: curl -s " + INDEX_URL
        : "Unable to load the release index (" + err.message + ").");
    });
})();
