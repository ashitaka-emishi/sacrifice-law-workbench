# Future LangGraph / LangChain Compatibility

V1 does not require LangGraph or LangChain.

The current implementation uses explicit scripts, manifests, schemas, status
files, source-specific download skills, and rebuild commands.

However, the scaffold is LangGraph-ready:

- each historical case can later become a LangGraph case subgraph;
- `x-case` can later become a synthesis subgraph;
- each pipeline stage can later become a graph node;
- human review gates should map cleanly to future interrupt/resume checkpoints;
- user-assisted corpus acquisition should map cleanly to future pause/resume workflows;
- the corpus acquisition layer can later become a standalone scholarly
  acquisition engine with deterministic provider adapters and optional
  LangGraph orchestration;
- durable state should be serializable to JSON/YAML files;
- no critical pipeline state should exist only in memory or chat history.

## Possible future graph

```text
project-graph
  ├── case-subgraph: am-rev
  ├── case-subgraph: napoleon
  ├── case-subgraph: lincoln
  ├── case-subgraph: hitler
  └── x-case-synthesis-subgraph
```
