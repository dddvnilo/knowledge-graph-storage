# Data

RDF that goes into the store, as TriG (`.trig`): each structure in its own named graph, together with its provenance. Every `.trig` file under this folder, including subfolders, is loaded by `python tools/kg.py rebuild --yes` (see [`../store.toml`](../store.toml)).

Empty until the data model (T3) and ingest (T5) exist.
