#!/usr/bin/env python3
"""
kg.py - small command-line tool for the ks-graph Virtuoso store.

Commands:
  status    [--wait SECONDS]                      check that the store is reachable
  graphs    [--all]                               list named graphs with triple counts
  load      FILE [--graph IRI] [--replace]        load RDF; TriG/N-Quads are split per named graph
  query     QUERY_OR_FILE [--format table|csv|json]   run a SPARQL query (read-only)
  update    UPDATE_OR_FILE                        run a SPARQL update (authenticated)
  drop      --graph IRI                           delete one named graph
  reset     --yes                                 delete all non-system named graphs
  rebuild   [--manifest FILE] --yes               empty the store, then load everything in store.toml
  selftest                                        load, query and delete a tiny test dataset

Connection settings (command-line options override environment variables):
  KG_ENDPOINT   base URL of Virtuoso        (default: http://localhost:8890)
  KG_USER       user for writes             (default: dba)
  KG_PASSWORD   password for writes         (fallback: DBA_PASSWORD, also read from infra/.env)

Writes use the SPARQL 1.1 Graph Store HTTP Protocol (one HTTP request per named graph).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import tomllib
from pathlib import Path

import requests
from requests.auth import HTTPDigestAuth
from rdflib import Dataset, Graph, URIRef

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "infra" / ".env"

# Graphs that Virtuoso creates for itself; hidden by `graphs` and never touched by `reset`.
SYSTEM_GRAPH_PREFIXES = (
    "http://www.openlinksw.com/",
    "http://www.w3.org/",
    "http://localhost:8890/",
    "urn:activitystreams-owl:map",
    "urn:core:services:",
    "urn:rdf12:",          # Virtuoso 7.2.17
    "virtrdf",
)

RDF_FORMATS = {
    ".trig": "trig",
    ".nq": "nquads",
    ".ttl": "turtle",
    ".nt": "nt",
    ".rdf": "xml",
    ".owl": "xml",
    ".jsonld": "json-ld",
}
QUAD_FORMATS = {"trig", "nquads"}


# --------------------------------------------------------------------------- config

def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Store:
    def __init__(self, endpoint: str, user: str, password: str | None, timeout: float = 60):
        self.base = endpoint.rstrip("/")
        self.user = user
        self.password = password
        self.timeout = timeout

    # --- helpers
    def _auth(self) -> HTTPDigestAuth:
        if not self.password:
            sys.exit("No password for writes. Set KG_PASSWORD or DBA_PASSWORD (or infra/.env).")
        return HTTPDigestAuth(self.user, self.password)

    @staticmethod
    def _check(resp: requests.Response, what: str) -> requests.Response:
        if resp.status_code >= 400:
            sys.exit(f"{what} failed: HTTP {resp.status_code}\n{resp.text[:1000]}")
        return resp

    # --- reading
    def ping(self) -> bool:
        try:
            r = requests.get(f"{self.base}/sparql", params={"query": "ASK {}"},
                             headers={"Accept": "application/sparql-results+json"}, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def select(self, query: str) -> dict:
        r = requests.post(f"{self.base}/sparql", data={"query": query},
                          headers={"Accept": "application/sparql-results+json"}, timeout=self.timeout)
        return self._check(r, "Query").json()

    def raw_query(self, query: str, accept: str) -> str:
        r = requests.post(f"{self.base}/sparql", data={"query": query},
                          headers={"Accept": accept}, timeout=self.timeout)
        return self._check(r, "Query").text

    # --- writing
    def update(self, update: str) -> None:
        r = requests.post(f"{self.base}/sparql-auth", data={"query": update},
                          auth=self._auth(), timeout=self.timeout)
        self._check(r, "Update")

    def put_graph(self, graph_iri: str, turtle: str, replace: bool) -> None:
        method = requests.put if replace else requests.post
        r = method(f"{self.base}/sparql-graph-crud-auth", params={"graph-uri": graph_iri},
                   data=turtle.encode("utf-8"),
                   headers={"Content-Type": "text/turtle; charset=utf-8"},
                   auth=self._auth(), timeout=self.timeout)
        self._check(r, f"Upload of <{graph_iri}>")

    def drop_graph(self, graph_iri: str) -> None:
        self.update(f"DROP SILENT GRAPH <{graph_iri}>")

    def graph_counts(self) -> list[tuple[str, int]]:
        res = self.select("SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g ORDER BY ?g")
        return [(b["g"]["value"], int(b["n"]["value"])) for b in res["results"]["bindings"]]


def is_system_graph(iri: str) -> bool:
    return iri.startswith(SYSTEM_GRAPH_PREFIXES)


def read_text_arg(value: str) -> str:
    """A query argument may be a file path or the query text itself."""
    p = Path(value)
    if p.suffix in {".rq", ".sparql", ".ru"} or (len(value) < 300 and p.is_file()):
        return p.read_text(encoding="utf-8")
    return value


# --------------------------------------------------------------------------- commands

def cmd_status(store: Store, args) -> None:
    deadline = time.time() + (args.wait or 0)
    while True:
        if store.ping():
            print(f"OK: {store.base}/sparql is reachable")
            return
        if time.time() >= deadline:
            sys.exit(f"Not reachable: {store.base}/sparql")
        time.sleep(2)


def cmd_graphs(store: Store, args) -> None:
    rows = [(g, n) for g, n in store.graph_counts() if args.all or not is_system_graph(g)]
    if not rows:
        print("(no named graphs)")
        return
    width = max(len(g) for g, _ in rows)
    for g, n in rows:
        print(f"{g:<{width}}  {n:>8}")


def parse_rdf_file(path: Path, graph: str | None) -> list[tuple[str, Graph]]:
    """Parse one RDF file into (graph IRI, triples) pairs without touching the store.

    Quad formats keep their own graph names; `graph` is used for single-graph
    formats and for TriG triples written outside any GRAPH block.
    """
    fmt = RDF_FORMATS.get(path.suffix.lower())
    if fmt is None:
        sys.exit(f"{path}: unknown RDF file extension (known: {', '.join(RDF_FORMATS)})")
    try:
        if fmt in QUAD_FORMATS:
            ds = Dataset()
            ds.parse(path, format=fmt)
            result = []
            for g in sorted(ds.graphs(), key=lambda g: str(g.identifier)):
                if len(g) == 0:
                    continue
                iri = str(g.identifier)
                if iri.startswith("urn:x-rdflib:"):          # triples outside any GRAPH block
                    if not graph:
                        sys.exit(f"{path} has {len(g)} triples outside named graphs; "
                                 f"give a target graph for them.")
                    iri = graph
                result.append((iri, g))
            return result
        if not graph:
            sys.exit(f"{path}: {path.suffix} holds a single graph; give a target graph.")
        g = Graph()
        g.parse(path, format=fmt)
        return [(graph, g)]
    except SystemExit:
        raise
    except Exception as e:                                # rdflib raises many parser-specific types
        sys.exit(f"{path}: cannot parse as {fmt}: {e}")


def cmd_load(store: Store, args) -> None:
    for iri, g in parse_rdf_file(Path(args.file), args.graph):
        store.put_graph(iri, g.serialize(format="turtle"), replace=args.replace)
        print(f"{'replaced' if args.replace else 'loaded  '} <{iri}>  {len(g)} triples")


def read_manifest(path: Path) -> list[tuple[Path, str | None]]:
    """Expand the manifest into (file, target graph) pairs, in manifest order."""
    if not path.exists():
        sys.exit(f"Manifest not found: {path}")
    try:
        entries = tomllib.loads(path.read_text(encoding="utf-8")).get("load", [])
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"{path}: {e}")
    files: list[tuple[Path, str | None]] = []
    for i, entry in enumerate(entries, start=1):
        pattern = entry.get("files")
        if not pattern:
            sys.exit(f"{path}: [[load]] entry {i} has no `files`.")
        matches = sorted(p for p in REPO_ROOT.glob(pattern) if p.is_file())
        if not matches:
            print(f"warning: {path.name} entry {i}: `{pattern}` matches no files", file=sys.stderr)
        files.extend((p, entry.get("graph")) for p in matches)
    return files


def cmd_rebuild(store: Store, args) -> None:
    manifest = Path(args.manifest)
    files = read_manifest(manifest)

    # Parse everything first: a broken file must not leave a half-emptied store.
    uploads: list[tuple[Path, str, Graph]] = []
    for path, graph in files:
        uploads.extend((path, iri, g) for iri, g in parse_rdf_file(path, graph))

    targets = [g for g, _ in store.graph_counts() if not is_system_graph(g)]
    if not args.yes:
        print("Would drop:\n  " + "\n  ".join(targets or ["(nothing)"]))
        print("Would load:")
        for path, iri, g in uploads:
            print(f"  {path.relative_to(REPO_ROOT).as_posix()} -> <{iri}>  {len(g)} triples")
        print("Run again with --yes to do it.")
        return

    for g in targets:
        store.drop_graph(g)
    print(f"dropped {len(targets)} graph(s)")
    # The store is empty now, so appending is safe and lets several files fill one graph.
    for path, iri, g in uploads:
        store.put_graph(iri, g.serialize(format="turtle"), replace=False)
        print(f"loaded  {path.relative_to(REPO_ROOT).as_posix()} -> <{iri}>  {len(g)} triples")
    print("rebuild done")


def cmd_query(store: Store, args) -> None:
    query = read_text_arg(args.query)
    if args.format == "json":
        print(json.dumps(store.select(query), indent=2, ensure_ascii=False))
        return
    if args.format == "turtle":
        print(store.raw_query(query, "text/turtle"))
        return

    res = store.select(query)
    if "boolean" in res:
        print(res["boolean"])
        return
    cols = res["head"]["vars"]
    rows = [[b.get(c, {}).get("value", "") for c in cols] for b in res["results"]["bindings"]]
    if args.format == "csv":
        w = csv.writer(sys.stdout)
        w.writerow(cols)
        w.writerows(rows)
        return
    widths = [max([len(c)] + [len(r[i]) for r in rows]) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * widths[i] for i in range(len(cols))))
    for r in rows:
        print("  ".join(v.ljust(widths[i]) for i, v in enumerate(r)))
    print(f"({len(rows)} rows)")


def cmd_update(store: Store, args) -> None:
    store.update(read_text_arg(args.update))
    print("OK")


def cmd_drop(store: Store, args) -> None:
    store.drop_graph(args.graph)
    print(f"dropped <{args.graph}>")


def cmd_reset(store: Store, args) -> None:
    targets = [g for g, _ in store.graph_counts() if not is_system_graph(g)]
    if not args.yes:
        print("Would drop:\n  " + "\n  ".join(targets or ["(nothing)"]))
        print("Run again with --yes to drop them.")
        return
    for g in targets:
        store.drop_graph(g)
        print(f"dropped <{g}>")


SELFTEST_TRIG = """
@prefix ex: <urn:ks-graph:selftest:> .
ex:graph-a { ex:i1 ex:linkedTo ex:i2 . ex:i2 ex:linkedTo ex:i3 . }
ex:graph-b { ex:i1 ex:linkedTo ex:i2 . }
"""


def cmd_selftest(store: Store, args) -> None:
    a, b = "urn:ks-graph:selftest:graph-a", "urn:ks-graph:selftest:graph-b"
    steps = []
    try:
        if not store.ping():
            sys.exit(f"FAIL: {store.base}/sparql is not reachable")
        steps.append("endpoint reachable")

        ds = Dataset()
        ds.parse(data=SELFTEST_TRIG, format="trig")
        for g in ds.graphs():
            if len(g):
                store.put_graph(str(g.identifier), g.serialize(format="turtle"), replace=True)
        steps.append("upload via Graph Store protocol (authenticated)")

        counts = dict(store.graph_counts())
        assert counts.get(a) == 2 and counts.get(b) == 1, f"unexpected counts: {counts.get(a)}, {counts.get(b)}"
        steps.append("named graphs kept separate")

        diff = store.select(f"""SELECT ?s ?o WHERE {{
            GRAPH <{a}> {{ ?s <urn:ks-graph:selftest:linkedTo> ?o }}
            FILTER NOT EXISTS {{ GRAPH <{b}> {{ ?s <urn:ks-graph:selftest:linkedTo> ?o }} }} }}""")
        rows = [(x["s"]["value"], x["o"]["value"]) for x in diff["results"]["bindings"]]
        assert rows == [("urn:ks-graph:selftest:i2", "urn:ks-graph:selftest:i3")], rows
        steps.append("cross-graph comparison query (FILTER NOT EXISTS)")

        mdiff = store.select(f"""SELECT ?s ?o WHERE {{
            GRAPH <{a}> {{ ?s <urn:ks-graph:selftest:linkedTo> ?o }}
            MINUS {{ GRAPH <{b}> {{ ?s <urn:ks-graph:selftest:linkedTo> ?o }} }} }}""")
        rows = [(x["s"]["value"], x["o"]["value"]) for x in mdiff["results"]["bindings"]]
        assert rows == [("urn:ks-graph:selftest:i2", "urn:ks-graph:selftest:i3")], rows
        steps.append("cross-graph comparison query (MINUS)")

        closure = store.select(f"""ASK {{ GRAPH <{a}> {{
            <urn:ks-graph:selftest:i1> <urn:ks-graph:selftest:linkedTo>+ <urn:ks-graph:selftest:i3> }} }}""")
        assert closure["boolean"] is True
        steps.append("property path with both ends bound")

        # The one form of a full closure that Virtuoso 7.2.17 answers (see infra/README.md):
        # Virtuoso's own OPTION (TRANSITIVE) with the start bound by a join. Two closures
        # in one query fail, so comparisons of closures need stored closure graphs.
        p = "<urn:ks-graph:selftest:linkedTo>"
        cl = store.select(f"""SELECT DISTINCT ?s ?o WHERE {{
            GRAPH <{a}> {{ ?s {p} ?x }}
            {{ SELECT ?s ?o WHERE {{ GRAPH <{a}> {{ ?s {p} ?o }} }} }}
            OPTION (TRANSITIVE, t_distinct, t_in(?s), t_out(?o), t_min(1)) }}""")
        rows = sorted((x["s"]["value"].rsplit(":", 1)[-1], x["o"]["value"].rsplit(":", 1)[-1])
                      for x in cl["results"]["bindings"])
        assert rows == [("i1", "i2"), ("i1", "i3"), ("i2", "i3")], rows
        steps.append("transitive closure of one graph (OPTION TRANSITIVE)")
    finally:
        for g in (a, b):
            try:
                store.drop_graph(g)
            except SystemExit:
                pass
    steps.append("cleanup (DROP GRAPH)")
    for s in steps:
        print(f"OK  {s}")
    print("selftest passed")


# --------------------------------------------------------------------------- main

def main(argv=None) -> None:
    env = {**read_env_file(ENV_FILE), **os.environ}
    parser = argparse.ArgumentParser(description="ks-graph Virtuoso tool", formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("Commands:")[0].strip())
    parser.add_argument("--endpoint", default=env.get("KG_ENDPOINT", "http://localhost:8890"))
    parser.add_argument("--user", default=env.get("KG_USER", "dba"))
    parser.add_argument("--password", default=env.get("KG_PASSWORD") or env.get("DBA_PASSWORD"))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="check that the store is reachable")
    p.add_argument("--wait", type=float, default=0, help="keep retrying for this many seconds")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("graphs", help="list named graphs with triple counts")
    p.add_argument("--all", action="store_true", help="also show Virtuoso's system graphs")
    p.set_defaults(func=cmd_graphs)

    p = sub.add_parser("load", help="load an RDF file")
    p.add_argument("file")
    p.add_argument("--graph", help="target graph for single-graph files, or for triples outside GRAPH blocks in TriG")
    p.add_argument("--replace", action="store_true", help="replace graph contents instead of adding to them")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("query", help="run a read-only SPARQL query")
    p.add_argument("query", help="query text or path to a .rq file")
    p.add_argument("--format", choices=["table", "csv", "json", "turtle"], default="table")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("update", help="run a SPARQL update")
    p.add_argument("update", help="update text or path to a .ru/.rq file")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("drop", help="delete one named graph")
    p.add_argument("--graph", required=True)
    p.set_defaults(func=cmd_drop)

    p = sub.add_parser("reset", help="delete all non-system named graphs")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_reset)

    p = sub.add_parser("rebuild", help="empty the store and load everything listed in the manifest")
    p.add_argument("--manifest", default=str(REPO_ROOT / "store.toml"))
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_rebuild)

    p = sub.add_parser("selftest", help="end-to-end check of the store")
    p.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    store = Store(args.endpoint, args.user, args.password)
    args.func(store, args)


if __name__ == "__main__":
    main()
