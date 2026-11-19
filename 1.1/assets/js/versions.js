/*
 * Versioned docs (ADR 0011). The site root holds versions.json (mike format):
 *   [{"version": "1.1", "title": "1.1", "aliases": ["latest"]}, {"version": "dev", ...}]
 * The theme renders the version selector from it. This script works out, at
 * runtime, whether the page being read belongs to the latest release, to `dev`
 * (built from main, unreleased) or to an older release, then:
 *   - sets <html data-gkm-version="dev|old"> (versions.css recolours the header
 *     and tabs: orange for dev, grey for older releases), and
 *   - shows a notice with a link to the same page in the latest release.
 * Nothing is baked into a build, so an older version turns grey on its own when
 * a newer release ships. The result is cached for the tab (sessionStorage) so the
 * next page can colour its header before versions.json loads.
 */
(function () {
  "use strict";

  var configEl = document.getElementById("__config");
  if (!configEl) return;

  var base = new URL(JSON.parse(configEl.textContent).base.replace(/\/?$/, "/"), location.href);
  var current = base.pathname.replace(/\/$/, "").split("/").pop();
  var root = new URL("../", base);
  var cacheKey = "gkm-docs-state:" + base.pathname;

  function samePageIn(version) {
    var rel = location.pathname.indexOf(base.pathname) === 0
      ? location.pathname.slice(base.pathname.length) : "";
    return new URL(version + "/" + rel, root);
  }

  function render(info) {
    if (info.state === "dev" || info.state === "old") {
      document.documentElement.setAttribute("data-gkm-version", info.state);
    } else {
      document.documentElement.removeAttribute("data-gkm-version");
    }

    var old = document.querySelector(".gkm-version-banner");
    if (old) old.remove();
    if (info.state !== "dev" && info.state !== "old") return;

    var link = null;
    if (info.latest) {
      var target = samePageIn(info.latest);
      link = document.createElement("a");
      link.href = target.href + location.search + location.hash;
      link.textContent = "Go to this page in the latest release (" + info.latestTitle + ")";
      // Keep the reader's current #section when they follow the link.
      link.addEventListener("click", function () {
        link.href = link.href.split("#")[0].split("?")[0] + location.search + location.hash;
      });
      // A page that doesn't exist in the latest release falls back to its home.
      fetch(target.href, { method: "HEAD" }).then(function (r) {
        if (!r.ok) link.href = new URL(info.latest + "/", root).href;
      }).catch(function () {});
    }

    var inner = document.createElement("div");
    inner.className = "md-banner__inner md-grid md-typeset";
    var lead = document.createElement("strong");
    if (info.state === "dev") {
      lead.textContent = "Development docs: not for production use.";
      inner.appendChild(lead);
      inner.appendChild(document.createTextNode(
        " These pages are built from the main branch and describe unreleased changes, which may still change" +
        " before release." + (link ? " " : "")));
    } else {
      lead.textContent = "You are reading the docs for " + info.title + ", which is not the current version.";
      inner.appendChild(lead);
      inner.appendChild(document.createTextNode(" "));
    }
    if (link) {
      inner.appendChild(link);
      inner.appendChild(document.createTextNode("."));
    }

    var banner = document.createElement("aside");
    banner.className = "md-banner gkm-version-banner gkm-version-banner--" + info.state;
    banner.setAttribute("role", "note");
    banner.appendChild(inner);
    var header = document.querySelector(".md-header");
    if (header && header.parentNode) header.parentNode.insertBefore(banner, header);
  }

  try {
    var cached = sessionStorage.getItem(cacheKey);
    if (cached) render(JSON.parse(cached));
  } catch (e) {}

  fetch(new URL("versions.json", root).href, { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (versions) {
      var hasAlias = function (v, a) { return (v.aliases || []).indexOf(a) >= 0; };
      var latest = versions.filter(function (v) { return hasAlias(v, "latest"); })[0];
      var mine = versions.filter(function (v) { return v.version === current || hasAlias(v, current); })[0];
      var info = { state: "" };
      if (mine) {
        info.title = mine.title || mine.version;
        if (latest) { info.latest = latest.version; info.latestTitle = latest.title || latest.version; }
        if (latest && mine.version === latest.version) info.state = "latest";
        else if (mine.version === "dev") info.state = "dev";
        else if (latest) info.state = "old";
      }
      try { sessionStorage.setItem(cacheKey, JSON.stringify(info)); } catch (e) {}
      render(info);
    })
    .catch(function () {}); // a local build has no versions.json: plain page
})();
