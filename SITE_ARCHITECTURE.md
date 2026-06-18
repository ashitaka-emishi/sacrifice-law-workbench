# Site Architecture

The Quarto site separates the public scholarly reading path from the larger
auditable workbench. Simplifying navigation must not delete evidence, break
stable URLs, or make validation material undiscoverable.

## Primary reader path

The navbar has five destinations:

1. **Overview** introduces the question, provisional answer, cases, and reading
   paths.
2. **Findings** is the cross-case argument hub.
3. **Cases** introduces case selection and links to four case hubs.
4. **Method** explains the canonical analytical sequence and links to detailed
   protocols.
5. **Research Archive** indexes status, governance, validation, provenance,
   publication, and infrastructure pages.

The default sidebar remains deliberately short. Detailed synthesis and analysis
pages are reached through the Findings and Cases hubs rather than repeated in
global navigation.

## Naming policy

Publication navigation uses reader-facing labels. Internal filenames remain
stable when changing them would break links:

- `starter-corpus-proposal.qmd` renders as **Corpus and Sources**.
- `starter-cluster-proposal.qmd` renders as **Metaphor Systems**.
- `cases/x-case/artifacts/qmd/x-case-overview.qmd` renders as **Findings**.

## Status pages

The two status artifacts have distinct roles and are linked together only in
the archive:

- `project-status.qmd` is generated from pipeline state.
- `CURRENT_STATUS.md` is the maintained narrative audit.

## Maintenance rules

- Keep the navbar at no more than six reader destinations.
- Keep the default sidebar at no more than 15 links.
- Add detailed pages to an appropriate hub before adding global navigation.
- Preserve search access and stable URLs for archival pages.
- Keep generated hub content in its generator so pipeline rebuilds do not undo
  navigation improvements.
- Validate changes with the project pipeline, Quarto render, link inspection,
  and desktop/mobile review.
