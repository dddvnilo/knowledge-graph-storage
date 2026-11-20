#!/usr/bin/env python3
"""
check_rdf.py - checks the RDF files listed in store.toml against rules of the data model
that a SPARQL store does not enforce. Works on the files, no store needed.

  python tools/check_rdf.py [--manifest FILE]

Checks:
  closure   every closure graph (ks:closureGraph) is exactly the transitive closure,
            without reflexive links, of the prerequisite links in the structure's content graph
  scope     every ks:requires / ks:prerequisiteOf link in a content graph stays inside
            the scope the structure declares (ks:coversItem, ks:coversCompetency)

Exit code 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rdflib import Dataset, Graph, Namespace, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kg  # noqa: E402

KS = Namespace("https://example.org/ks#")


def load(manifest: Path) -> Dataset:
    ds = Dataset()
    for path, graph in kg.read_manifest(manifest):
        for iri, g in kg.parse_rdf_file(path, graph):
            target = ds.graph(URIRef(iri))
            for t in g:
                target.add(t)
    return ds


def closure(pairs: set[tuple]) -> set[tuple]:
    result = set(pairs)
    while True:
        new = {(a, d) for a, b in result for c, d in result if b == c and a != d} - result
        if not new:
            return result
        result |= new


def check(ds: Dataset) -> list[str]:
    errors: list[str] = []
    graphs = {g.identifier: g for g in ds.graphs()}

    def content(iri) -> Graph:
        return graphs.get(iri, Graph())

    for structure, _, closure_iri, _ in ds.quads((None, KS.closureGraph, None, None)):
        stated = {(s, o) for s, o in content(structure).subject_objects(KS.prerequisiteOf)}
        stored = {(s, o) for s, o in content(closure_iri).subject_objects(KS.prerequisiteOf)}
        expected = closure(stated)
        if stored != expected:
            def show(pairs):
                return ", ".join(f"<{a}> -> <{b}>" for a, b in sorted(pairs)) or "none"
            errors.append(f"closure of <{structure}>: missing {show(expected - stored)}; "
                          f"unexpected {show(stored - expected)}")

    for structure in {s for s, _, _, _ in ds.quads((None, KS.coversItem, None, None))} | \
                     {s for s, _, _, _ in ds.quads((None, KS.coversCompetency, None, None))}:
        g = content(structure)
        scope = set(g.objects(structure, KS.coversItem)) | set(g.objects(structure, KS.coversCompetency))
        for p in (KS.requires, KS.prerequisiteOf):
            for s, o in g.subject_objects(p):
                outside = [x for x in (s, o) if x not in scope]
                if outside:
                    errors.append(f"<{structure}>: <{s}> {p.n3()} <{o}> uses "
                                  f"{', '.join(f'<{x}>' for x in outside)} outside the declared scope")
    return errors


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--manifest", default=str(kg.REPO_ROOT / "store.toml"))
    args = parser.parse_args(argv)
    errors = check(load(Path(args.manifest)))
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        sys.exit(1)
    print("check_rdf passed")


if __name__ == "__main__":
    main()
