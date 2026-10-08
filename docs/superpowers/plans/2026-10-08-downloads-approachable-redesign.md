# Downloads Approachable Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the single Downloads page into a left-nav group (hub + 4 child pages), add a shared R2 browser with per-type views and R2 availability dates, surface weekly Parquet deltas, and collapse recipes — making the page approachable for returning and new users alike.

**Architecture:** `index.json` (built by `generate-r2-index.sh`) gains a `modified` date on every entry and a per-delta `parquet` section list. One shared `docs/assets/js/r2-browser.js` reads `index.json` once and renders a view chosen by each mount's `data-r2-type`. `download.md` becomes a short hub; four new child pages (`monthly-full.md`, `weekly-deltas.md`, `parquet.md`, `release-model.md`) each host a scoped browser + collapsed recipes. The Downloads nav entry becomes a group using the repo's existing bare-index pattern.

**Tech Stack:** Zensical (Material theme, `zensical build --strict`), vanilla JS (no deps, CSP-safe), bash 3.2 + AWS CLI (`aws s3 ls` against Cloudflare R2), Markdown with `pymdownx.details` collapsible call-outs.

**Spec:** `docs/superpowers/specs/2026-10-07-downloads-page-approachable-redesign-design.md`

**Branch:** `docs/downloads-approachable-redesign` (off `1.0`). Verifies with `zensical build --strict` and `zensical serve`; the generator verifies with `--dry-run` (read-only on R2). **Live `index.json` regeneration/upload to R2 is a separate, user-confirmed step and is NOT part of this plan.**

**Conventions:** This is docs/JS/bash, not a unit-tested library — each task's "test" is a concrete command (strict build, dry-run output inspection, grep of built/served HTML) with expected output. Bash stays 3.2-compatible (no `mapfile`, no `declare -A`). Preserve heading *text* for referenced anchors: `Weekly Deltas`, `Consumer Replay Model`, `Parquet Files`, `Download`, `Applying Deltas (keeping a Parquet set current)`.

---

## Chunk 1: index.json generator — dates + per-delta Parquet

### Task 1: Add `modified` dates and per-delta `parquet` lists to `generate-r2-index.sh`

**Files:**
- Modify: `src/scripts/generate-r2-index.sh`

**Background:** `aws s3 ls <prefix>` prints `DATE TIME SIZE NAME` for files and `PRE name/` for sub-dirs. Today `r2_ls_with_size` keeps `$3,$4` (size,name) and directory-based entries (deltas, parquet sets) carry no date. See spec §6/§7.

- [ ] **Step 1: Capture the date in `r2_ls_with_size`**

Modify the awk in `r2_ls_with_size` (currently `{print $3, $4}`) to emit the date too:

```bash
r2_ls_with_size() {
  # Returns "DATE SIZE FILENAME" lines for .json.gz files under a prefix
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null | awk '/\.json\.gz$/ {print $1, $3, $4}' || true
}
```

- [ ] **Step 2: Thread the date through `build_file_array`**

Update the read loop and the emitted JSON object to include `modified`:

```bash
build_file_array() {
  local prefix="$1" latest_name="$2"
  local first=true
  local arr="["

  while IFS=' ' read -r modified size filename; do
    [[ -z "$filename" ]] && continue
    if ! $first; then arr+=","; fi
    first=false

    local is_latest="false"
    if [[ -n "$latest_name" && "$filename" == "$latest_name" ]]; then
      is_latest="true"
    fi

    arr+=$(printf '{"name":"%s","path":"%s%s","size":%s,"modified":"%s","latest":%s}' \
      "$filename" "$prefix" "$filename" "$size" "$modified" "$is_latest")
  done < <(r2_ls_with_size "$prefix")

  arr+="]"
  echo "$arr"
}
```

- [ ] **Step 3: Add two helper functions** (after `r2_ls_with_size`)

```bash
# Newest immediate-file date (YYYY-MM-DD) under a prefix, or empty.
# Skips "PRE dir/" lines (they have no date in $1).
r2_newest_date_under() {
  local prefix="$1"
  aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --profile "${R2_PROFILE}" \
    2>/dev/null \
    | awk '$1 ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/ {print $1}' \
    | sort | tail -n1 || true
}

# JSON array of parquet section names (filename minus .parquet) under a prefix.
r2_parquet_sections_under() {
  local prefix="$1"
  local first=true
  local arr="["
  while IFS= read -r section; do
    [[ -z "$section" ]] && continue
    if ! $first; then arr+=","; fi
    first=false
    arr+=$(printf '"%s"' "$section")
  done < <(
    aws s3 ls "s3://${R2_BUCKET}/${prefix}" \
      --endpoint-url "${R2_ENDPOINT}" \
      --profile "${R2_PROFILE}" \
      2>/dev/null | awk '/\.parquet$/ {sub(/\.parquet$/, "", $NF); print $NF}' || true
  )
  arr+="]"
  echo "$arr"
}
```

- [ ] **Step 4: Add `modified` to Parquet set entries in `build_parquet_array`**

Inside the loop, after `release`/`is_latest` are set, compute the date and add the field:

```bash
    local modified
    modified="$(r2_newest_date_under "${prefix}${dir}/")"

    arr+=$(printf '{"release":"%s","path":"%s%s/","modified":"%s","latest":%s}' \
      "$release" "$prefix" "$dir" "$modified" "$is_latest")
```

- [ ] **Step 5: Add `modified` + `parquet` to delta entries in `build_deltas_array`**

Inside the loop, after `path`/`is_latest` are set:

```bash
    local modified parquet_sections
    modified="$(r2_newest_date_under "deltas/${dir}/")"
    parquet_sections="$(r2_parquet_sections_under "deltas/${dir}/parquet/")"

    arr+=$(printf '{"release":"%s","path":"%s","manifest":"%smanifest.json","modified":"%s","parquet":%s,"latest":%s}' \
      "$release" "$path" "$path" "$modified" "$parquet_sections" "$is_latest")
```

- [ ] **Step 6: Lint**

Run: `bash -n src/scripts/generate-r2-index.sh && shellcheck src/scripts/generate-r2-index.sh`
Expected: no syntax errors; no new shellcheck warnings beyond pre-existing.

- [ ] **Step 7: Dry-run against live R2 (read-only) and inspect the candidate index**

Run:
```bash
src/scripts/generate-r2-index.sh --dry-run
python3 -m json.tool /tmp/clinvar-gkm-index.json | \
  grep -E '"modified"|"parquet"|"name"|"release"' | head -40
```
Expected: monthly entries show `"modified":"YYYY-MM-DD"`; each delta shows `"modified"` and a `"parquet":[...]` array of section names; parquet sets show `"modified"`. No upload occurs (`--dry-run` gates `r2_upload`). If any `modified` is empty, re-check the awk field positions against `aws s3 ls` output.

- [ ] **Step 8: Commit**

```bash
git add src/scripts/generate-r2-index.sh
git commit -m "feat(r2-index): add modified dates + per-delta parquet lists to index.json"
```

---

## Chunk 2: Shared R2 browser component

### Task 2: Create `docs/assets/js/r2-browser.js` and wire it in

**Files:**
- Create: `docs/assets/js/r2-browser.js`
- Modify: `zensical.toml` (line 10, `extra_javascript`)

This generalizes the inline script currently in `download.md` into a reusable, mount-driven component. It renders five view types and shows `modified` dates when present. It no-ops when no `.r2-browser` mount exists on the page.

- [ ] **Step 1: Write `docs/assets/js/r2-browser.js`**

```javascript
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
```

- [ ] **Step 2: Add the component to `extra_javascript`**

In `zensical.toml` line 10, add the new file (keep any existing entry):

```toml
extra_javascript = ["assets/js/keyboard-shortcuts.js", "assets/js/r2-browser.js"]
```

> Merge note: the search-fix PR #120 removes `keyboard-shortcuts.js` from this list. When both land on `1.0`, reconcile to `extra_javascript = ["assets/js/r2-browser.js"]`.

- [ ] **Step 3: Add styles** to `docs/stylesheets/extra.css`. These supersede the per-page `<style>` block in the old `download.md` (removed in Task 9) and are shared by all child pages. The new JS uses only `.r2-folder / .r2-file / .r2-size / .r2-date / .r2-latest / .r2-error`; the old page's `.r2-badge / .r2-group / .r2-section` classes are unused and dropped. Port the old disclosure-triangle (`.r2-folder > summary::before`) and `.r2-file a` link styling into the block below if you want visual parity.

Add to `docs/stylesheets/extra.css`:

```css
.r2-browser { font-family: var(--md-code-font-family); font-size: 0.82rem; line-height: 1.6; }
.r2-folder > summary { cursor: pointer; font-weight: 600; padding: 0.15rem 0; }
.r2-file { padding: 0.1rem 0 0.1rem 0.4rem; }
.r2-size, .r2-date { color: var(--md-default-fg-color--light); font-size: 0.75rem; margin-left: 0.5rem; }
.r2-latest { width: 100%; border-collapse: collapse; }
.r2-latest th, .r2-latest td { text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid var(--md-default-fg-color--lightest); }
.r2-error { padding: 0.8rem; border-left: 3px solid var(--md-accent-fg-color); margin: 1rem 0; }
```

- [ ] **Step 4: Build**

Run: `zensical build --strict`
Expected: "No issues found" (JS + CSS referenced; no page mounts yet, so the script no-ops).

- [ ] **Step 5: Commit**

```bash
git add docs/assets/js/r2-browser.js zensical.toml docs/stylesheets/extra.css
git commit -m "feat(docs): shared r2-browser.js with per-type mounts + date rendering"
```

---

## Chunk 3: Child pages, nav, link migration, hub

**Ordering note (keeps `--strict` green at every commit):** the four child pages all cross-link one another, and Zensical builds + validates every `.md` regardless of nav — so a build passes only once **all four exist**. Therefore Tasks 3–6 create the pages but **do not build or commit individually**; Task 6 builds `--strict` and commits all four **together**. After that: Task 7 nav → Task 8 migrate inbound links → Task 9 slim `download.md`. `download.md` keeps its content and anchors until Task 9, so inbound links stay valid until Task 8 migrates them.

### Task 3: Create `docs/data-access/release-model.md` (How Releases Work)

**Files:** Create `docs/data-access/release-model.md`

- [ ] **Step 1:** Create the page. Move the conceptual content from `download.md`: the full+delta intro (lines ~5–11), the month-start-baseline framing, and the **Release Cadence** section (download.md ~889–898). Add an intro line and a sibling cross-link row:

```markdown
# How Releases Work

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md)

<full+delta model prose moved from download.md>

## Release Cadence
<moved from download.md; keep the 2026-07 ← 2026-06-27 example>
```

The canonical `manifest.json` field table is NOT here — link to Weekly Deltas for it.

- [ ] **Step 2:** Do NOT build or commit yet — the sibling cross-links (`weekly-deltas.md`, `monthly-full.md`, `parquet.md`) resolve only once those pages exist; Task 6 builds + commits all four together.

### Task 4: Create `docs/data-access/weekly-deltas.md`

**Files:** Create `docs/data-access/weekly-deltas.md`

- [ ] **Step 1:** Create the page. Include a `deltas` browser mount, the Delta Bundle + canonical `manifest.json` field table (moved from download.md ~129–163), and the **Consumer Replay Model** section (moved from ~165–237) with its code in a collapsed `???`. Preserve heading text `Weekly Deltas` and `Consumer Replay Model`.

```markdown
# Weekly Deltas

Links: [Monthly Full Bundles](monthly-full.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

<div class="r2-browser" data-r2-type="deltas"></div>

## Delta Bundle
<moved prose>

### manifest.json
<moved field table — canonical>

### Consumer Replay Model
<moved prose; concept visible>

??? example "Python: rebuild the current full bundle from deltas"
    ```python
    <moved replay code from download.md ~171-237>
    ```
```

- [ ] **Step 2:** Do NOT build or commit yet (Task 6 does). Note: `#consumer-replay-model` will exist on BOTH this page and `download.md` until Task 9 — that is fine; duplicate anchors across pages are legal and `--strict` doesn't check fragments.

### Task 5: Create `docs/data-access/monthly-full.md`

**Files:** Create `docs/data-access/monthly-full.md`

- [ ] **Step 1:** Create the page with a `monthly` browser mount, sibling cross-links, and collapsed curl/Python download recipes (from download.md ~27–106, scoped to a monthly full).

```markdown
# Monthly Full Bundles

Links: [Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md) · [How Releases Work](release-model.md)

<div class="r2-browser" data-r2-type="monthly"></div>

??? example "Download a monthly full with curl / Python"
    ```bash
    <moved curl snippet>
    ```
```

- [ ] **Step 2:** Do NOT build or commit yet (Task 6 does).

### Task 6: Create `docs/data-access/parquet.md`

**Files:** Create `docs/data-access/parquet.md`

- [ ] **Step 1:** Create the page with TWO browser mounts and the reconstitution reference. Move the Parquet content from download.md (~536–885). Preserve `Parquet Files` and `Applying Deltas (keeping a Parquet set current)` headings. Fix BOTH stale "20 sections" occurrences → "22" (the `Available Parquet files (20 sections)` heading and the `# Or download all 20 sections` comment in the bash loop). Collapse DuckDB/pandas query recipes and rebuild scripts; keep the reconstitution concept visible.

```markdown
# Parquet Files

Links: [Monthly Full Bundles](monthly-full.md) · [Weekly Deltas](weekly-deltas.md) · [How Releases Work](release-model.md)

## Monthly full sets
<div class="r2-browser" data-r2-type="parquet-monthly"></div>

## Weekly Parquet deltas
Changed-rows delta Parquet (not a full set) — one group per weekly release.
<div class="r2-browser" data-r2-type="parquet-weekly"></div>

<column reference + "Available Parquet files (22 sections)" + query prose>

??? example "Query with DuckDB / pandas"
    ```bash
    <moved query recipes>
    ```

### Reconstitute a full Parquet view for any week in a month
<visible concept: bootstrap checkpoint monthly full set → apply each weekly delta Parquet
(added/updated rows) + manifest sections.<s>.deleted ids, oldest→newest, up to the chosen week>

??? example "Apply one week (DuckDB)"
    ```python
    <moved "Apply one delta" code>
    ```

??? example "Chain to a specific week (Python)"
    ```python
    <generalized "Chaining multiple weeks" code — target week is a parameter>
    ```
```

- [ ] **Step 2:** All four child pages now exist, so their sibling cross-links resolve. `zensical build --strict` → "No issues found". Commit the four pages together:

```bash
git add docs/data-access/release-model.md docs/data-access/weekly-deltas.md docs/data-access/monthly-full.md docs/data-access/parquet.md
git commit -m "docs: add Downloads child pages (release-model, weekly-deltas, monthly-full, parquet)"
```

### Task 7: Convert the Downloads nav entry into a group

**Files:** Modify `zensical.toml` (line 14)

- [ ] **Step 1:** Replace `{ Downloads = "data-access/download.md" },` with the group (bare index = hub, mirroring the existing "Data Model" pattern):

```toml
  { Downloads = [
    "data-access/download.md",
    { "Monthly Full Bundles" = "data-access/monthly-full.md" },
    { "Weekly Deltas"        = "data-access/weekly-deltas.md" },
    { "Parquet Files"        = "data-access/parquet.md" },
    { "How Releases Work"    = "data-access/release-model.md" },
  ] },
```

- [ ] **Step 2:** `zensical build --strict` → "No issues found"; confirm the Downloads group with four children appears in the left nav (checked in Task 10 serve). Commit.

### Task 8: Migrate inbound links (spec §5.7)

**Files:** Modify `docs/getting-started.md`, `docs/data-access/index.md`, `docs/data-access/output-files.md`, `docs/pipeline/export.md`, `docs/user-story-audit.md`, `docs/index.md`

- [ ] **Step 1 — anchored links:**
  - `getting-started.md:8` → `data-access/weekly-deltas.md#consumer-replay-model`
  - `data-access/index.md:10` → `weekly-deltas.md#consumer-replay-model`
  - `data-access/output-files.md:30` → `weekly-deltas.md#consumer-replay-model`
  - `data-access/output-files.md:60` → `weekly-deltas.md`
  - `pipeline/export.md:119` → `../data-access/parquet.md`
  - `pipeline/export.md:164` → `../data-access/weekly-deltas.md`
  - `user-story-audit.md:19,121` → `data-access/parquet.md`

- [ ] **Step 2 — bare/prose links:**
  - `docs/index.md:159` → split: manifest → `data-access/release-model.md`, replay → `data-access/weekly-deltas.md`
  - `data-access/index.md:25` → `weekly-deltas.md` and `parquet.md`
  - `user-story-audit.md:130` → `data-access/parquet.md`
  - `pipeline/export.md:170` → reword: per-type browsers on the child pages

- [ ] **Step 3:** `grep -rnoE "download\.md" docs/ --exclude-dir=superpowers` → confirm no stale references remain outside the hub file `download.md` itself. `zensical build --strict` → "No issues found". Commit.

### Task 9: Slim `download.md` to the hub

**Files:** Modify `docs/data-access/download.md`

- [ ] **Step 1:** Replace the body with the hub: a one-line intro (link to How Releases Work), the **Latest Release** browser mount, a short **Directory Structure** block (kept from the old page), and **Feedback**. Remove the old inline browser `<script>`/`<style>` (now in `r2-browser.js`/`extra.css`), the moved Weekly Deltas/Parquet/Cadence sections, and the now-migrated anchors.

```markdown
# Downloads

ClinVar-GKM is distributed as a monthly full bundle plus weekly deltas (JSON + typed Parquet),
free from Cloudflare R2. New here? See [How Releases Work](release-model.md).

## Latest Release
<div class="r2-browser" data-r2-type="latest"></div>

Browse history and archives: [Monthly Full Bundles](monthly-full.md) ·
[Weekly Deltas](weekly-deltas.md) · [Parquet Files](parquet.md).

## Directory Structure
<kept from old page>

## Feedback
<kept from old page>
```

- [ ] **Step 2:** `zensical build --strict` → "No issues found" (all links to the removed anchors were migrated in Task 8). Commit.

---

## Chunk 4: End-to-end verification

### Task 10: Serve and verify the whole experience

**Files:** none (verification only)

- [ ] **Step 1: Build a local index.json with the new fields** to exercise date + weekly-Parquet rendering before any live R2 regen:

`r2-browser.js` hard-codes `INDEX_URL` to the absolute R2 URL, so a local `site/index.json` is NOT fetched. To exercise the new `modified`/`parquet` fields, temporarily repoint `INDEX_URL`: run `src/scripts/generate-r2-index.sh --dry-run`, copy `/tmp/clinvar-gkm-index.json` to `docs/assets/local-index.json`, set `INDEX_URL` in `r2-browser.js` to that relative path, then `zensical serve`. **Revert the `INDEX_URL` edit and delete `local-index.json` before committing.**

- [ ] **Step 2: Verify rendering**

```bash
BASE=http://localhost:8000
# Static HTML contains the mount divs, NOT the JS-rendered table — grep the mounts:
curl -sL "$BASE/clinvar-gkm/data-access/download/" | grep -oc 'data-r2-type="latest"'  # hub mount = 1
curl -sL "$BASE/clinvar-gkm/data-access/parquet/"  | grep -oc 'data-r2-type='           # parquet mounts = 2
```
Expected: hub page has 1 `latest` mount; parquet page has 2 mounts. (Adjust the hub path if the bare-index page resolves to `/data-access/` rather than `/data-access/download/`.) The JS-rendered `r2-latest` table + dates are verified **in a browser** (curl can't run JS): the Downloads group shows 4 children in the left nav; dates render on entries; the Weekly Parquet deltas browser lists per-delta sections; sibling cross-links and the hub's `../parquet/` "browse sets" link resolve.

- [ ] **Step 3: Graceful fallback check** — point the browser at the *current* live index.json (no `modified`/`parquet`): dates are absent, weekly-Parquet groups are empty, nothing shows "undefined". Expected: no errors; behaves like today minus dates.

- [ ] **Step 4: Strict build + stale-link sweep**

```bash
zensical build --strict          # Expected: No issues found
grep -rnoE "download\.md#" docs/ --exclude-dir=superpowers  # Expected: no matches
```

- [ ] **Step 5: Manual anchor check** — open `weekly-deltas.md#consumer-replay-model` and `weekly-deltas.md#weekly-deltas` in the served site; confirm they resolve (`--strict` does not validate fragments).

- [ ] **Step 6: Push + open PR into `1.0`**

```bash
git push -u origin docs/downloads-approachable-redesign
gh pr create --base 1.0 --title "docs: Downloads nav group + R2 dates + weekly Parquet (1.0.1 RC)" --body "<summary>"
```

---

## Follow-up (NOT in this plan — user-confirmed separate step)

Regenerate and upload `index.json` to live R2 (`generate-r2-index.sh` without `--dry-run`) so dates and the weekly-Parquet browser populate on the deployed site. This is a live-R2 write requiring explicit user confirmation; until then the browser degrades gracefully.
