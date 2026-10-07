#!/usr/bin/env python3
"""Convert YAML schema source files to Markdown class definition files.

Generates Markdown suitable for Zensical (Material theme) from the same
ga4gh.gkm.metaschema YAML sources that y2t uses for RST. Each public class
gets a .md file in the md/ output directory with:

  - Maturity admonition
  - Computational definition
  - Information model table (Field | Type | Limits | Description)
  - Link to generated JSON schema

For classes composed via allOf, inherited fields from parent classes are
resolved and included in the information model table.
"""

import os
import pathlib
import re
import sys
import urllib.request
import zlib
from pathlib import Path

from ga4gh.gkm.metaschema.tools.source_proc import YamlSchemaProcessor

# Cache of loaded processors keyed by resolved source file path
_processor_cache: dict[str, YamlSchemaProcessor] = {}

# Set of class names that have local pages (populated at build time)
_local_classes: set[str] = set()

# Extension* class name -> its protectedClassOf parent class (built per source
# run in main()). Extension classes are rendered as sub-sections on their
# parent's page rather than as standalone pages.
_extension_parent: dict[str, str] = {}

# Class names that have a published docs page (loaded in main() from the docs
# classes dir). Used to avoid emitting links to pages that are not published —
# e.g. an extension whose protectedClassOf parent is an abstract/undefined class.
_published_classes: set[str] = set()

# --- Upstream docs cross-reference resolution (Sphinx objects.inv) -----------
# Links to upstream classes point at the docs for the SAME release the schema
# sources pin (via /ga4gh/schema/<spec>/<ver>/ $refs). Each GA4GH docs site is a
# Sphinx build whose objects.inv keys classes as lowercased std:label entries
# (e.g. "sequencelocation" -> ".../SequenceLocation.html#$"); gkm-core classes
# are documented within the VRS site.
_SPEC_SITES = {
    "vrs": "https://vrs.ga4gh.org/en/",
    "cat-vrs": "https://cat-vrs.ga4gh.org/en/",
    "va-spec": "https://va-spec.ga4gh.org/en/",
}
# Precedence when a class appears in more than one inventory: va-spec, then
# cat-vrs, then vrs (first hit wins). Shared classes (e.g. Allele) are in all.
_INVENTORY_ORDER = ("va-spec", "cat-vrs", "vrs")

_inventories: dict[str, dict | None] = {}   # {base_url: {label: url} | None}
_doc_bases: dict[str, str] = {}              # {spec: resolved docs base URL}
# vrs docs base for the maturity-model admonition link (overridden in main()).
_maturity_base = "https://vrs.ga4gh.org/en/stable/"


def _load_inventory(base: str) -> dict | None:
    """Fetch + parse the Sphinx objects.inv at `base`; cache by base URL.

    Returns {lowercased_label: absolute_url}, or None if it can't be loaded.
    """
    if base in _inventories:
        return _inventories[base]
    result: dict | None = None
    try:
        req = urllib.request.Request(
            base + "objects.inv",
            headers={"User-Agent": "Mozilla/5.0 (clinvar-gkm docs generator)"})
        raw = urllib.request.urlopen(req, timeout=20).read()
        # Header = 4 text lines, then a zlib-compressed block of
        # "name domain:role priority uri dispname" lines.
        nl = idx = 0
        while nl < 4:
            if raw[idx:idx + 1] == b"\n":
                nl += 1
            idx += 1
        entries: dict[str, str] = {}
        for line in zlib.decompress(raw[idx:]).decode("utf-8", "replace").splitlines():
            m = re.match(r"(.+?)\s+(\S+)\s+(-?\d+)\s+(\S+)\s+(.*)", line)
            if not m:
                continue
            label, role, _prio, uri, _disp = m.groups()
            if role == "std:label":
                entries.setdefault(label, base + uri.replace("$", label))
        result = entries
    except Exception:  # offline / 5xx / 404 candidate / parse error (not fatal)
        result = None
    _inventories[base] = result
    return result


def _pinned_versions(sources_dir: Path) -> dict[str, str]:
    """Versions the schema sources pin per spec, from /ga4gh/schema/<spec>/<ver>/."""
    pat = re.compile(r"/ga4gh/schema/(vrs|cat-vrs|va-spec)/([0-9][0-9.]*)/")
    pins: dict[str, str] = {}
    for src in sorted(sources_dir.glob("*-source.yaml")):
        for spec, ver in pat.findall(src.read_text()):
            pins[spec] = ver
    return pins


def _candidate_paths(version: str) -> list[str]:
    """RTD path candidates for a pinned version: exact, major.minor, stable."""
    cands = [version]
    parts = version.split(".")
    if len(parts) >= 2:
        cands.append(f"{parts[0]}.{parts[1]}")
    cands += ["stable", "latest"]
    seen: set[str] = set()
    return [c for c in cands if not (c in seen or seen.add(c))]


def _resolve_doc_bases(sources_dir: Path) -> None:
    """Resolve each spec's docs base to the first candidate (for its pinned
    version) that publishes an objects.inv, and set the vrs maturity-link base."""
    global _maturity_base
    pins = _pinned_versions(sources_dir)
    for spec, site in _SPEC_SITES.items():
        version = pins.get(spec)
        if not version:
            continue
        for cand in _candidate_paths(version):
            base = f"{site}{cand}/"
            if _load_inventory(base) is not None:
                _doc_bases[spec] = base
                break
        if spec not in _doc_bases:
            print(f"  [y2md] WARNING: no reachable docs for {spec} (pinned "
                  f"{version}); its types will render unlinked", file=sys.stderr)
    if "vrs" in _doc_bases:
        _maturity_base = _doc_bases["vrs"]


def _resolve_upstream(class_name: str) -> str | None:
    """Resolve an upstream class to its pinned-release docs URL, or None.

    Precedence across sites is va-spec, then cat-vrs, then vrs (first hit wins).
    """
    key = class_name.lower()
    for spec in _INVENTORY_ORDER:
        base = _doc_bases.get(spec)
        if not base:
            continue
        inv = _load_inventory(base)
        if inv and key in inv:
            return inv[key]
    return None


def _get_processor(source_path: Path) -> YamlSchemaProcessor:
    """Get or create a cached YamlSchemaProcessor for a source file."""
    key = str(source_path.resolve())
    if key not in _processor_cache:
        _processor_cache[key] = YamlSchemaProcessor(source_path)
    return _processor_cache[key]


def _format_type_ref(identifier: str) -> str:
    """Link a non-primitive type: extension anchor, local page, or upstream docs.

    Precedence:
      1. Extension* class -> anchor on its protectedClassOf parent page (no own page).
      2. Local class with its own page -> relative .md link.
      3. Upstream class (vrs/cat-vrs/gkm-core/va-spec) -> deployed docs URL (new tab).
      4. Otherwise -> plain code (never a broken link).
    """
    parent = _extension_parent.get(identifier)
    if parent:
        if parent in _published_classes:
            return f"[{identifier}]({parent}.md#{identifier.lower()})"
        # Parent has no published page (abstract/undefined protectedClassOf) —
        # render plain so we never emit a broken link.
        return f"`{identifier}`"
    # Local classes get their own page — but Extension* pages are dropped (they
    # render as parent sub-sections), so never link an extension to `<name>.md`.
    if identifier in _local_classes and not identifier.startswith("Extension"):
        return f"[{identifier}]({identifier}.md)"
    url = _resolve_upstream(identifier)
    if url:
        return f"[{identifier}]({url}){{ target=_blank rel=noopener }}"
    return f"`{identifier}`"


def resolve_type(prop_def: dict) -> str:
    """Resolve a property definition to a type string."""
    if "type" in prop_def:
        if prop_def["type"] == "array":
            inner = resolve_type(prop_def.get("items", {}))
            return f"{inner}[]"
        return f"`{prop_def['type']}`"
    elif "$ref" in prop_def:
        identifier = prop_def["$ref"].split("/")[-1]
        return _format_type_ref(identifier)
    elif "$refCurie" in prop_def:
        identifier = prop_def["$refCurie"].rpartition(":")[2]
        return _format_type_ref(identifier)
    elif "oneOf" in prop_def or "anyOf" in prop_def:
        kw = "oneOf" if "oneOf" in prop_def else "anyOf"
        parts = []
        for item in prop_def[kw]:
            parts.append(resolve_type(item))
        return " \\| ".join(parts)
    return "_unspecified_"


def resolve_cardinality(prop_name: str, prop_attrs: dict, class_def: dict) -> str:
    """Resolve property cardinality."""
    required = class_def.get("required", []) + class_def.get("heritableRequired", [])
    min_count = "1" if prop_name in required else "0"
    if prop_attrs.get("type") == "array":
        max_count = prop_attrs.get("maxItems", "m")
        min_count = str(prop_attrs.get("minItems", 0))
    else:
        max_count = "1"
    return f"{min_count}..{max_count}"


def resolve_flags(prop_attrs: dict) -> str:
    """Resolve property flags (ordered, maturity)."""
    flags = []
    if prop_attrs.get("type") == "array":
        ordered = prop_attrs.get("ordered", False)
        flags.append("ordered" if ordered else "unordered")
    maturity = prop_attrs.get("maturity", "")
    if maturity == "draft":
        flags.append("draft")
    elif maturity == "deprecated":
        flags.append("deprecated")
    return ", ".join(flags)


def get_ancestor_with_attributes(ancestor, proc_schema):
    """Walk up the inheritance chain to find an ancestor with attributes."""
    while ancestor:
        ancestor_def = proc_schema.raw_defs.get(ancestor, {})
        if "heritableProperties" in ancestor_def or "properties" in ancestor_def:
            return ancestor
        ancestor = ancestor_def.get("inherits")
    return ancestor


def _resolve_ref_class_name(ref_item: dict) -> str | None:
    """Extract class name from a $ref or $refCurie."""
    if "$ref" in ref_item:
        return ref_item["$ref"].split("/")[-1]
    if "$refCurie" in ref_item:
        # $refCurie uses namespace:ClassName format
        return ref_item["$refCurie"].split(":")[-1]
    return None


def _find_class_in_processors(class_name: str, proc_schema) -> dict | None:
    """Find a class definition across the processor and its imports."""
    # Check the main processor
    if class_name in proc_schema.defs:
        return proc_schema.defs[class_name]
    # Check imported processors
    for imp_proc in proc_schema.imports.values():
        result = _find_class_in_processors(class_name, imp_proc)
        if result is not None:
            return result
    return None


def _get_class_properties(class_name: str, proc_schema) -> dict:
    """Get all properties for a class, including inherited ones via allOf."""
    class_def = _find_class_in_processors(class_name, proc_schema)
    if class_def is None:
        return {}

    props = {}

    # First, collect properties from allOf parents (inherited fields first)
    for ref_item in class_def.get("allOf", []):
        parent_name = _resolve_ref_class_name(ref_item)
        if parent_name:
            parent_props = _get_class_properties(parent_name, proc_schema)
            props.update(parent_props)

    # Then collect properties inherited via the inherits keyword
    # (already resolved by YamlSchemaProcessor into heritableProperties)

    # Finally, add local properties (override inherited ones)
    for key in ("heritableProperties", "properties"):
        if key in class_def and class_def[key]:
            props.update(class_def[key])
            break

    return props


def _write_props_table(f, props: dict, owner_def: dict):
    """Write a Field/Type/Limits/Description table for a set of properties."""
    f.write("| Field | Type | Limits | Description |\n")
    f.write("| --- | --- | --- | --- |\n")
    for prop_name, prop_attrs in props.items():
        prop_type = resolve_type(prop_attrs)
        cardinality = resolve_cardinality(prop_name, prop_attrs, owner_def)
        desc = prop_attrs.get("description", "").replace("\n", " ").replace("|", "\\|")
        flags = resolve_flags(prop_attrs)
        if flags:
            prop_type = f"{prop_type} ({flags})"
        f.write(f"| `{prop_name}` | {prop_type} | {cardinality} | {desc} |\n")
    f.write("\n")


def _write_extension_sections(f, class_name: str, proc_schema):
    """Render Extension* classes whose protectedClassOf is `class_name` as
    sub-sections (they have no standalone page). The `### <Extension>` heading
    yields the anchor that references elsewhere link to."""
    extensions = sorted(e for e, p in _extension_parent.items() if p == class_name)
    if not extensions:
        return
    f.write("## Extensions\n\n")
    f.write(f"These extensions are defined for `{class_name}`.\n\n")
    for ext in extensions:
        ext_def = _find_class_in_processors(ext, proc_schema) or {}
        f.write(f"### {ext}\n\n")
        desc = ext_def.get("description", "")
        if desc:
            f.write(f"{desc}\n\n")
        ext_props = _get_class_properties(ext, proc_schema)
        if ext_props:
            _write_props_table(f, ext_props, ext_def)


def write_class_md(class_name: str, class_def: dict, proc_schema, out_dir: Path,
                   json_schema_base: str):
    """Write a single class Markdown file."""
    out_file = out_dir / f"{class_name}.md"

    with open(out_file, "w") as f:
        # Title
        f.write(f"# {class_name}\n\n")

        # Maturity admonition
        maturity = class_def.get("maturity", "")
        maturity_link = (
            f"[GKM Maturity Model]({_maturity_base}appendices/maturity_model.html)"
            "{ target=_blank rel=noopener }")
        if maturity == "draft":
            f.write('!!! warning "Draft"\n\n')
            f.write(f"    May change significantly in future releases. "
                    f"See the {maturity_link}.\n\n")
        elif maturity == "trial use":
            f.write('!!! note "Trial Use"\n\n')
            f.write(f"    May change in future releases. See the {maturity_link}.\n\n")

        # Computational definition
        description = class_def.get("description", "")
        f.write(f"{description}\n\n")

        # JSON schema link
        f.write(f"**JSON Schema:** "
                f"[{class_name}]({json_schema_base}/{class_name})"
                f"{{ target=_blank }}\n\n")

        # Show oneOf/anyOf members if present
        for kw in ("oneOf", "anyOf"):
            if kw in class_def:
                f.write("**One of:**\n\n")
                for item in class_def[kw]:
                    item_type = resolve_type(item)
                    f.write(f"- {item_type}\n")
                f.write("\n")

        # Collect all properties including inherited via allOf
        all_props = _get_class_properties(class_name, proc_schema)

        # Identify allOf parents for the inheritance note
        allof_parents = []
        for ref_item in class_def.get("allOf", []):
            parent_name = _resolve_ref_class_name(ref_item)
            if parent_name:
                allof_parents.append(parent_name)

        if not all_props:
            # No own fields (union, allOf-only, or primitive). Still render any
            # extension sub-sections this class parents, then stop.
            _write_extension_sections(f, class_name, proc_schema)
            return

        # Inheritance note
        ancestor = proc_schema.raw_defs[class_name].get("inherits")
        if ancestor:
            ancestor = get_ancestor_with_attributes(ancestor, proc_schema)
            if ancestor:
                f.write(f"Some {class_name} attributes are inherited from "
                        f"{_format_type_ref(ancestor)}.\n\n")
        elif allof_parents:
            parent_links = ", ".join(
                _format_type_ref(p) for p in allof_parents
            )
            f.write(f"Some {class_name} attributes are inherited from "
                    f"{parent_links}.\n\n")

        # Information model table
        f.write("## Information Model\n\n")
        _write_props_table(f, all_props, class_def)

        # Extension sub-sections (Extension* classes protectedClassOf this class)
        _write_extension_sections(f, class_name, proc_schema)


def _load_local_classes(build_dir: Path):
    """Load all local class names from .classes files in the build directory."""
    if not build_dir.exists():
        return
    for classes_file in build_dir.glob("*.classes"):
        for line in classes_file.read_text().splitlines():
            name = line.strip()
            if name:
                _local_classes.add(name)


def main(proc_schema):
    """Generate Markdown files for all public classes."""
    md_dir = proc_schema.def_fp.parent / "md"
    os.makedirs(md_dir, exist_ok=True)

    # Load all local class names for link resolution
    build_dir = proc_schema.def_fp.parent / "build"
    _load_local_classes(build_dir)

    # Resolve upstream docs bases to the release the sources pin.
    _resolve_doc_bases(md_dir.parent)

    # Cache the main processor
    _processor_cache[str(proc_schema.schema_fp.resolve())] = proc_schema

    # Map Extension* classes to their protectedClassOf parent. These render as
    # sub-sections on the parent's page, not as standalone pages, so references
    # to them resolve to `<parent>.md#<extension-lowercased>`.
    for cname in proc_schema.defs:
        pco = proc_schema.raw_defs.get(cname, {}).get("protectedClassOf")
        if cname.startswith("Extension") and pco:
            _extension_parent[cname] = pco

    # Classes with a published docs page (the sync only updates existing pages).
    # Used so we never link to a page that will not exist (e.g. an extension
    # whose protectedClassOf parent is abstract/undefined).
    docs_classes = (md_dir.parent.parent.parent
                    / "docs" / "output-reference" / "classes")
    if docs_classes.is_dir():
        for page in docs_classes.glob("*.md"):
            _published_classes.add(page.stem)

    # Base URL for JSON schema links (relative from docs site)
    json_schema_base = (
        "https://github.com/clingen-data-model/clinvar-gkm/blob/main"
        "/schema/clinvar-gkm/json"
    )

    for class_name, class_def in proc_schema.defs.items():
        if class_name in _extension_parent:
            continue  # rendered as a sub-section on its protectedClassOf parent
        write_class_md(class_name, class_def, proc_schema, out_dir=md_dir,
                       json_schema_base=json_schema_base)


def cli():
    source_file = pathlib.Path(sys.argv[1])
    p = YamlSchemaProcessor(source_file)
    if p.defs is None:
        exit(0)
    main(p)


if __name__ == "__main__":
    cli()
