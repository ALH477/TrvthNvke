# Truthgate

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
equals: 0.2.0
-->
Current version: **0.2.0**.
<!-- truth:end -->

## Install

<!-- truth:claim
id: cli-module
kind: file_exists
path: src/truthgate/cli.py
-->
The CLI entry is `src/truthgate/cli.py`, exposed as the `truthgate` console script.
<!-- truth:end -->

<!-- truth:claim
id: mcp-module
kind: file_exists
path: src/truthgate/mcp_server.py
-->
The agent server is `src/truthgate/mcp_server.py`.
<!-- truth:end -->

```bash truth:id=help truth:kind=command truth:expect_exit=0 truth:expect_stdout=Force README
PYTHONPATH=src python3 -m truthgate --help
```

From a checkout:

```bash truth:id=editable-help truth:kind=command truth:expect_exit=0 truth:expect_stdout=0.2.0
PYTHONPATH=src python3 -m truthgate --version
```

## Usage

```bash truth:id=extract-self truth:kind=command truth:expect_exit=0 truth:expect_stdout=cli-module
PYTHONPATH=src python3 -m truthgate extract --doc README.md
```

```bash truth:id=schema truth:kind=command truth:expect_exit=0 truth:expect_stdout=file_exists
PYTHONPATH=src python3 -m truthgate schema
```

Structured edits (what the MCP applies):

```json truth:ignore
[
  {
    "op": "upsert_claim",
    "id": "cli-module",
    "kind": "file_exists",
    "path": "src/truthgate/cli.py",
    "after_heading": "Install",
    "body": "The CLI entry is `src/truthgate/cli.py`."
  }
]
```

```bash truth:id=edit-dry truth:kind=command truth:expect_exit=0
PYTHONPATH=src python3 -m truthgate edit --doc README.md --dry-run --ops '[{"op":"replace_claim_body","id":"version","body":"Current version: **0.2.0**."}]'
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
The NixOS module is `nix/module.nix` (`demod.truthgate.enable`).
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
    truthgate.url = "github:ALH477/truthgate";
  };

  outputs = { self, nixpkgs, flake-utils, truthgate }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ truthgate.overlays.default ];
        };
      in {
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.truthgate ];
        };
        checks.readme = pkgs.runCommand "truthgate-readme" {
          nativeBuildInputs = [ pkgs.truthgate ];
          src = self;
        } ''
          cp -r "$src"/. .
          chmod -R u+w .
          truthgate verify --fail
          touch "$out"
        '';
      });
}
```

From a published checkout:

```bash truth:ignore
nix flake init -t github:ALH477/truthgate
nix develop github:ALH477/truthgate
nix run github:ALH477/truthgate -- verify --fail
nix run github:ALH477/truthgate#mcp
```

Path override while this tree is still local:

```bash truth:ignore
nix develop github:ALH477/your-repo --override-input truthgate path:../truthgate
```

NixOS / Oligarchy-style import:

```nix truth:ignore
{
  inputs.truthgate.url = "github:ALH477/truthgate";
  outputs = { nixpkgs, truthgate, ... }: {
    nixosConfigurations.holdfast = nixpkgs.lib.nixosSystem {
      modules = [
        truthgate.nixosModules.default
        { demod.truthgate.enable = true; }
      ];
    };
  };
}
```

Outputs: `packages.truthgate`, `overlays.default`, `apps.truthgate`, `apps.mcp`, `devShells.default`, `nixosModules.default`, `templates.default`.

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
pattern: github:ALH477/truthgate
-->
`templates/consumer/flake.nix` pins `inputs.truthgate.url = "github:ALH477/truthgate"`.
<!-- truth:end -->

<!-- truth:claim
id: example-readme
kind: file_exists
path: templates/consumer/README.md
-->
`templates/consumer/README.md` is already claim-gated.
<!-- truth:end -->

```bash truth:id=example-verify truth:kind=command truth:expect_exit=0 truth:expect_stdout=PASS
PYTHONPATH=src python3 -m truthgate --root templates/consumer verify
```

What the example proves:

1. A DeMoD repo declares one flake input on **ALH477**.
2. The overlay puts `truthgate` on PATH inside `nix develop`.
3. `checks.readme` is a Nix gate equivalent to `truthgate verify --fail`.
4. The consumer README binds its own `flake.nix` so the import URL cannot silently change.

## TruthMD

TruthMD is GitHub-flavored Markdown plus hidden claim directives. Rendered README stays normal Markdown.

Block claim (HTML comment, invisible on GitHub):

```markdown truth:ignore
<!-- truth:claim
id: cli-module
kind: file_exists
path: src/truthgate/cli.py
severity: error
-->
The CLI entry is `src/truthgate/cli.py`.
<!-- truth:end -->
```

Fenced claim (the fence *is* the evidence):

~~~~markdown truth:ignore
```bash truth:id=help truth:kind=command truth:expect_exit=0
python3 -m truthgate --help
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
| `file_contains` | regex or substring in a file |
| `json_pointer` / `toml_key` | value at a pointer equals `equals` |
| `command` | shell command exit + optional stdout |
| `heading` | heading text exists |
| `rel_link` | relative target exists |
| `version_sync` | version file matches README |
| `prose` | tracked, not executed |

Policy lives in `.truthgate.toml`.

<!-- truth:claim
id: policy-file
kind: file_exists
path: .truthgate.toml
-->
This repository is gated by `.truthgate.toml`.
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
path: .github/workflows/truthgate.yml
-->
GitHub Actions workflow: `.github/workflows/truthgate.yml`.
<!-- truth:end -->

<!-- truth:claim
id: hook
kind: file_exists
path: hooks/pre-commit
-->
Local hook template: `hooks/pre-commit`. Install with `python3 -m truthgate install-hook`.
<!-- truth:end -->

Relative links that 404 become warnings (not merge blockers unless `fail_on = "warning"`).

## MCP

stdio MCP server for agents. No extra dependencies.

```json truth:ignore
{
  "mcpServers": {
    "truthgate": {
      "command": "python3",
      "args": ["-m", "truthgate", "mcp"],
      "cwd": "/path/to/repo"
    }
  }
}
```

Tools:

| Tool | Role |
| --- | --- |
| `truthgate_status` | policy + docs |
| `truthgate_list_claims` | extract claims |
| `truthgate_verify` | run gates |
| `truthgate_propose_edit` | dry-run ops |
| `truthgate_apply_edit` | apply ops; **reverts if gates fail** unless `force` |
| `truthgate_schema` | kinds + ops |

Allowed edit ops: `replace_claim_body`, `upsert_claim`, `remove_claim`, `replace_section`, `set_fence_meta`.

Agents must not rewrite the whole README. They propose ops, verify, then apply.

## Layout

<!-- truth:claim
id: package-layout
kind: glob_count
glob: src/truthgate/*.py
min: 8
-->
Implementation lives under `src/truthgate/` (parser, verifier, editor, MCP, CLI).
<!-- truth:end -->

## License

Apache-2.0. Copyright DeMoD LLC. See [LICENSE](LICENSE).
