# consumer

Example DeMoD repository that imports TrvthNvke.

Maintainer: [ALH477](https://github.com/ALH477) · [DeMoD LLC](https://demod.ltd)

## Install

Pull the flake from GitHub user **ALH477**:

```nix truth:ignore
{
  inputs.trvthnvke.url = "github:ALH477/TrvthNvke";
}
```

<!-- truth:claim
id: flake
kind: file_exists
path: flake.nix
-->
This tree ships `flake.nix` so other DeMoD repos can `nix develop` and get `trvthnvke` on PATH.
<!-- truth:end -->

<!-- truth:claim
id: flake-import
kind: file_contains
path: flake.nix
pattern: github:ALH477/TrvthNvke
-->
`flake.nix` pins `inputs.trvthnvke.url = "github:ALH477/TrvthNvke"`.
<!-- truth:end -->

## Usage

```bash truth:id=policy-present truth:kind=command truth:expect_exit=0
test -f .trvthnvke.toml
```

Enter the shell after you publish or path-override the input:

```bash truth:ignore
nix develop
trvthnvke verify --fail
```
