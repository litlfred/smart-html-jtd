// The DAK API hub page's one loader, published at `assets/dak-api-hub.js` by
// smart-base's `dak-api-hub-page.ts`. The page holds identity and a pointer to
// its node, `dak-api.jsonld`; this fetches the node and draws the sidecars,
// each with its artefact and view page, and the enumeration documents
// (`visualizer-loading`). Every string is set as text, never as HTML.
(function () {
  var kg = (window.__kgLoads = window.__kgLoads || {
    pending: 0,
    done: function () {
      if (--this.pending === 0) document.documentElement.setAttribute("data-kg-loaded", "");
    },
  });
  var cfgEl = document.getElementById("dak-api-hub");
  var host = document.querySelector(".dak-api-hub-body");
  if (!cfgEl || !host) return;
  var cfg = JSON.parse(cfgEl.textContent);

  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    (kids || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return e;
  }
  function link(href, label) {
    return href ? el("a", { href: href }, [label]) : "";
  }

  kg.pending++;
  fetch(cfg.node)
    .then(function (r) {
      if (!r.ok) throw new Error(r.status + " " + r.statusText);
      return r.json();
    })
    .then(function (node) {
      host.textContent = "";
      var parts = node["schema:hasPart"] || [];
      var byKind = {};
      parts.forEach(function (p) {
        var k = p["schema:additionalType"] || "Other";
        (byKind[k] = byKind[k] || []).push(p);
      });
      Object.keys(byKind).sort().forEach(function (k) {
        var rows = byKind[k].map(function (p) {
          var about = p["schema:about"];
          return el("tr", {}, [
            el("td", {}, [link(p["schema:contentUrl"], p["schema:name"])]),
            el("td", {}, [about ? link(about["@id"], about["schema:identifier"]) : "bound to no artefact"]),
            el("td", {}, [p["schema:url"] ? link(p["schema:url"], "view") : ""]),
          ]);
        });
        host.appendChild(el("h2", {}, [k + " (" + rows.length + ")"]));
        // `fa-page-wide`: the list fills the page layout's column (cat-harness-tools `page-layout.ts`).
        host.appendChild(el("table", { class: "fa-page-wide" }, [el("thead", {}, [el("tr", {}, [el("th", {}, ["File"]), el("th", {}, ["Artefact"]), el("th", {}, ["View"])])]), el("tbody", {}, rows)]));
      });
      var docs = node["schema:workExample"] || [];
      if (docs.length) {
        host.appendChild(el("h2", {}, ["Enumerations"]));
        host.appendChild(el("ul", {}, docs.map(function (d) { return el("li", {}, [link(d["schema:contentUrl"], d["schema:name"])]); })));
      }
    })
    .catch(function (e) {
      host.textContent = "Could not load " + cfg.node + ": " + e.message;
    })
    .then(function () { kg.done(); });
})();
