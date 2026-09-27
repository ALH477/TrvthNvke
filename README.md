<img src="docs/assets/trvthnvke-emblem.svg" alt="" width="72" height="72" align="right">

# TrvthNvke

[![gated by TrvthNvke](docs/assets/trvthnvke-badge.svg)](https://github.com/ALH477/TrvthNvke)

**DeMoD LLC** · maintained by [ALH477](https://github.com/ALH477)

Git-enforced READMEs for DeMoD repositories. Every checkable sentence is a claim. CI, a pre-commit hook, and a Nix flake refuse drift. Agents edit through a dedicated MCP, not by freehand rewrite.

<!-- truth:claim
id: org
kind: prose
-->
Published under GitHub user [ALH477](https://github.com/ALH477) for [DeMoD LLC](https://demod.ltd).
<!-- truth:end -->

<!-- truth:claim
id: version
kind: version_sync
path: pyproject.toml
key: project.version
equals: 0.4.0
-->
Current version: **0.4.0**.
<!-- truth:end -->

<!-- truth:claim
id: badge
kind: file_exists
path: docs/assets/trvthnvke-badge.svg
-->
The README badge is `docs/assets/trvthnvke-badge.svg`, committed here rather
than fetched from a shield service: no remote call, no embedded font, and every
label pinned with `textLength`, so it renders identically on GitHub, in an
offline Markdown preview and in a bare SVG viewer.
<!-- truth:end -->

<!-- truth:claim
id: emblem
kind: file_exists
path: docs/assets/trvthnvke-emblem.svg
-->
The mark is `docs/assets/trvthnvke-emblem.svg` — a radiation trefoil whose hub
is a seal. At favicon size the check collapses to a dot and the trefoil still
reads.
<!-- truth:end -->

## Install

<!-- truth:claim
id: cli-module
kind: file_exists
path: src/trvthnvke/cli.py
-->
The CLI entry is `src/trvthnvke/cli.py`.
<!-- truth:end -->

<!-- truth:claim
id: console-script
kind: entrypoint
name: trvthnvke
target: trvthnvke.cli:main
-->
It is exposed as the `trvthnvke` console script, wired to `trvthnvke.cli:main`.
<!-- truth:end -->

<!-- truth:claim
id: legacy-console-script
kind: entrypoint
name: truthgate
target: trvthnvke.cli:main
-->
This project was called **truthgate** before 0.4.0. The `truthgate` console
script is kept as an alias onto the same `trvthnvke.cli:main` entry point, and
`.truthgate.toml` / `truthgate.toml` are still accepted as policy filenames —
new names win where both exist. `tests/test_legacy_name.py` exercises that
fallback, so removing it fails the suite rather than silently breaking every
repository written against the old name.
<!-- truth:end -->

<!-- truth:claim
id: mcp-module
kind: file_exists
path: src/trvthnvke/mcp_server.py
-->
The agent server is `src/trvthnvke/mcp_server.py`.
<!-- truth:end -->

<!-- truth:claim
id: mcp-entry
kind: python_symbol
module: trvthnvke.mcp_server
symbol: run_stdio
-->
Its stdio loop is `run_stdio`, a real function, not a promise.
<!-- truth:end -->

```bash truth:id=help truth:kind=command truth:expect_exit=0 truth:expect_stdout=Force README
PYTHONPATH=src python3 -m trvthnvke --help
```

From a checkout:

```bash truth:id=editable-help truth:kind=command truth:expect_exit=0 truth:expect_stdout=0.4.0
PYTHONPATH=src python3 -m trvthnvke --version
```

## Usage

```bash truth:id=extract-self truth:kind=command truth:expect_exit=0 truth:expect_stdout=cli-module
PYTHONPATH=src python3 -m trvthnvke extract --doc README.md
```

```bash truth:id=schema truth:kind=command truth:expect_exit=0 truth:expect_stdout=file_exists
PYTHONPATH=src python3 -m trvthnvke schema
```

Structured edits (what the MCP applies):

```json truth:ignore
[
  {
    "op": "upsert_claim",
    "id": "cli-module",
    "kind": "file_exists",
    "path": "src/trvthnvke/cli.py",
    "after_heading": "Install",
    "body": "The CLI entry is `src/trvthnvke/cli.py`."
  }
]
```

```bash truth:id=edit-dry truth:kind=command truth:expect_exit=0
PYTHONPATH=src python3 -m trvthnvke edit --doc README.md --dry-run --ops '[{"op":"replace_claim_body","id":"version","body":"Current version: **0.4.0**."}]'
```

## Flake

<!-- truth:claim
id: flake-file
kind: file_exists
path: flake.nix
-->
The dedicated flake is `flake.nix`. Other DeMoD trees import it; they do not vendor the Python package.
<!-- truth:end -->

<!-- truth:claim
id: flake-package
kind: file_exists
path: nix/package.nix
-->
The package derivation lives in `nix/package.nix`.
<!-- truth:end -->

<!-- truth:claim
id: flake-module
kind: file_exists
path: nix/module.nix
-->
The NixOS module is `nix/module.nix` (`demod.trvthnvke.enable`).
<!-- truth:end -->

<!-- truth:claim
id: flake-brand
kind: file_contains
path: flake.nix
pattern: DeMoD LLC / ALH477
-->
`flake.nix` names **DeMoD LLC** and **ALH477**.
<!-- truth:end -->

Add the flake from GitHub user **ALH477**:

```nix truth:ignore
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    trvthnvke.url = "github:ALH477/TrvthNvke";
  };

  outputs = { self, nixpkgs, flake-utils, trvthnvke }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ trvthnvke.overlays.default ];
        };
      in {
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.trvthnvke ];
        };
        checks.readme = pkgs.runCommand "trvthnvke-readme" {
          nativeBuildInputs = [ pkgs.trvthnvke ];
          src = self;
        } ''
          cp -r "$src"/. .
          chmod -R u+w .
          trvthnvke verify --fail
          touch "$out"
        '';
      });
}
```

From a published checkout:

```bash truth:ignore
nix flake init -t github:ALH477/TrvthNvke
nix develop github:ALH477/TrvthNvke
nix run github:ALH477/TrvthNvke -- verify --fail
nix run github:ALH477/TrvthNvke#mcp
```

Path override while this tree is still local:

```bash truth:ignore
nix develop github:ALH477/your-repo --override-input trvthnvke path:../trvthnvke
```

NixOS / Oligarchy-style import:

```nix truth:ignore
{
  inputs.trvthnvke.url = "github:ALH477/TrvthNvke";
  outputs = { nixpkgs, trvthnvke, ... }: {
    nixosConfigurations.holdfast = nixpkgs.lib.nixosSystem {
      modules = [
        trvthnvke.nixosModules.default
        { demod.trvthnvke.enable = true; }
      ];
    };
  };
}
```

Outputs: `packages.trvthnvke`, `overlays.default`, `apps.trvthnvke`, `apps.mcp`, `devShells.default`, `nixosModules.default`, `templates.default`.

## Example

Worked consumer tree: [`templates/consumer`](templates/consumer).

<!-- truth:claim
id: example-flake
kind: file_exists
path: templates/consumer/flake.nix
-->
`templates/consumer/flake.nix` is the copy-paste import.
<!-- truth:end -->

<!-- truth:claim
id: example-import-url
kind: file_contains
path: templates/consumer/flake.nix
pattern: github:ALH477/TrvthNvke
-->
`templates/consumer/flake.nix` pins `inputs.trvthnvke.url = "github:ALH477/TrvthNvke"`.
<!-- truth:end -->

<!-- truth:claim
id: example-readme
kind: file_exists
path: templates/consumer/README.md
-->
`templates/consumer/README.md` is already claim-gated.
<!-- truth:end -->

```bash truth:id=example-verify truth:kind=command truth:expect_exit=0 truth:expect_stdout=PASS
PYTHONPATH=src python3 -m trvthnvke --root templates/consumer verify
```

What the example proves:

1. A DeMoD repo declares one flake input on **ALH477**.
2. The overlay puts `trvthnvke` on PATH inside `nix develop`.
3. `checks.readme` is a Nix gate equivalent to `trvthnvke verify --fail`.
4. The consumer README binds its own `flake.nix` so the import URL cannot silently change.

## TruthMD

TruthMD is GitHub-flavored Markdown plus hidden claim directives. Rendered README stays normal Markdown.

Block claim (HTML comment, invisible on GitHub):

```markdown truth:ignore
<!-- truth:claim
id: cli-module
kind: file_exists
path: src/trvthnvke/cli.py
severity: error
-->
The CLI entry is `src/trvthnvke/cli.py`.
<!-- truth:end -->
```

Fenced claim (the fence *is* the evidence):

~~~~markdown truth:ignore
```bash truth:id=help truth:kind=command truth:expect_exit=0
python3 -m trvthnvke --help
```
~~~~

Mark example-only fences so CI does not try to execute them:

~~~~markdown truth:ignore
```python truth:ignore
print("documentation sample")
```
~~~~

### Claim kinds

| Kind | What CI checks |
| --- | --- |
| `file_exists` / `dir_exists` | path is present |
| `glob_count` | `equals` / `min` / `max` against a glob |
| `file_contains` | literal `pattern` (or opt-in `regex`) present in a file |
| `json_pointer` / `toml_key` | value at a pointer equals `equals` |
| `command` | shell command exit + optional stdout |
| `heading` | heading text exists |
| `rel_link` | relative target exists |
| `version_sync` | version file matches README |
| `python_symbol` | module resolves under `python_roots`; optional `symbol` is defined at top level (static, via `ast`) |
| `entrypoint` | console script exists in `pyproject.toml`; optional `target` matches; target function is defined |
| `prose` | tracked, not executed |

`file_contains` matches a literal substring by default. Use `regex:` instead of `pattern:` to opt into Python `re` (256-char pattern cap, 2 MiB text cap, `regex_timeout_sec` timeout). Path-token coverage warnings scan every top-level directory of the repository unless `coverage_dirs` narrows the list.

Policy lives in `.trvthnvke.toml`.

<!-- truth:claim
id: policy-file
kind: file_exists
path: .trvthnvke.toml
-->
This repository is gated by `.trvthnvke.toml`.
<!-- truth:end -->

## CI gates

Gates fail a commit or PR when any of these fire at `error` severity:

- claim verifier returns false
- required heading missing
- fenced block has neither `truth:id` nor `truth:ignore`
- malformed / duplicate / unclosed claim
- documented file missing

<!-- truth:claim
id: workflow
kind: file_exists
path: .github/workflows/trvthnvke.yml
-->
GitHub Actions workflow: `.github/workflows/trvthnvke.yml`.
<!-- truth:end -->

<!-- truth:claim
id: hook
kind: file_exists
path: hooks/pre-commit
-->
Local hook template: `hooks/pre-commit`. Install with `python3 -m trvthnvke install-hook`.
<!-- truth:end -->

Relative links that 404 become warnings (not merge blockers unless `fail_on = "warning"`).

## MCP

stdio MCP server for agents. No extra dependencies.

```json truth:ignore
{
  "mcpServers": {
    "trvthnvke": {
      "command": "python3",
      "args": ["-m", "trvthnvke", "mcp"],
      "cwd": "/path/to/repo"
    }
  }
}
```

Tools:

| Tool | Role |
| --- | --- |
| `trvthnvke_status` | policy + docs |
| `trvthnvke_list_claims` | extract claims |
| `trvthnvke_verify` | run gates |
| `trvthnvke_propose_edit` | dry-run ops |
| `trvthnvke_apply_edit` | apply ops; **reverts if gates fail** unless `force` |
| `trvthnvke_schema` | kinds + ops |

Allowed edit ops: `replace_claim_body`, `upsert_claim`, `remove_claim`, `replace_section`, `set_fence_meta`.

Agents must not rewrite the whole README. They propose ops, verify, then apply.

## Layout

<!-- truth:claim
id: package-layout
kind: glob_count
glob: src/trvthnvke/*.py
min: 8
-->
Implementation lives under `src/trvthnvke/` (parser, verifier, editor, MCP, CLI).
<!-- truth:end -->

## License

Apache-2.0. Copyright DeMoD LLC. See [LICENSE](LICENSE).
