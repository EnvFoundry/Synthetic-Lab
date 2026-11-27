# External experiment data

Synthetic Lab keeps control state, operation metadata and small observations in the experiment
database. Large images, spectra, fields and trajectories are stored outside the relational record.
The result retains units, shape, axes and acquisition metadata while replacing only the large value
with an artifact reference.

```json
{
  "image": {
    "value": {
      "$artifact": {
        "id": "5f16a5f40e5d4cf5b4a1d8d9d329a5ae",
        "uri": "artifact://5f16a5f40e5d4cf5b4a1d8d9d329a5ae",
        "media_type": "application/json",
        "encoding": "utf-8",
        "size_bytes": 4823
      }
    },
    "unit": "count",
    "shape": [32, 32],
    "axes": ["row", "column"]
  }
}
```

The default threshold is 65,536 encoded bytes. Pass `artifact_threshold=None` to keep every JSON
value inline, or a smaller positive integer when developing a domain package. A file-backed database
uses a sibling `<database>.artifacts` directory. Clients and workers may instead share an explicit
store:

```python
from synthetic_lab import Lab, LocalArtifactStore

store = LocalArtifactStore("/shared/experiment-data")
with Lab("/shared/research.sqlite", artifact_store=store) as lab:
    experiment = lab.create("fluorescence-microscopy", seed=9)
```

The CLI accepts the same location before the subcommand:

```sh
synthetic-lab --db /shared/research.sqlite --artifacts /shared/experiment-data \
  worker --model fluorescence-microscopy
synthetic-lab --db /shared/research.sqlite --artifacts /shared/experiment-data \
  artifact-info ARTIFACT_ID
synthetic-lab --db /shared/research.sqlite --artifacts /shared/experiment-data \
  artifact ARTIFACT_ID image.json
```

`Lab.read_artifact()` returns the decoded JSON value. `Lab.iter_artifact()` yields bounded byte
chunks, and `Lab.export_artifact()` copies the stored representation without loading it in memory.
`Session.export()` keeps artifact references in JSONL, so long histories remain small and consumers
retrieve only the arrays they need.

Large persistent state follows the same rule. Before a model runs, its state references are
materialized inside the domain worker. After the operation, unchanged large values retain their
existing artifact IDs; changed values receive new IDs. A branch can therefore share unchanged
sample structure while preserving independent future evolution. An observation referring to the
same in-memory array as the state shares its stored object. Consecutive equal observation values
also retain their reference; this is temporal reuse, not a global content index.

MCP exposes `artifact_chunk(artifact_id, offset, limit)`. It returns base64 bytes, `next_offset`
and `eof`, with at most one MiB per response. Python provides `read_artifact_chunk` and the JSON-line
interface uses `artifact_chunk`. Public configuration reads do not load hidden field data.

The built-in store writes JSON. A cloud service can provide another object with `put_json`, `open`
and `discard` methods, backed by local files or a future object-storage adapter. Chunk access expects a seekable binary
stream from `open`. Binary domain formats still need codec support: current model-state loading
and `read_artifact` decode JSON. SQLite processes currently run on the same host.
