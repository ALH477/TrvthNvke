{
  description = "Example DeMoD repository importing TrvthNvke from github:ALH477/trvthnvke";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    trvthnvke.url = "github:ALH477/trvthnvke";
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
          packages = [ pkgs.trvthnvke pkgs.python3 pkgs.git ];
          shellHook = ''
            echo "TrvthNvke ready: $(command -v trvthnvke)"
            echo "Gate this tree with: trvthnvke verify --fail"
          '';
        };

        checks.readme = pkgs.runCommand "trvthnvke-readme" {
          nativeBuildInputs = [ pkgs.trvthnvke ];
          src = self;
        } ''
          cp -r "$src"/. .
          chmod -R u+w .
          trvthnvke verify --fail
          mkdir -p "$out"
          echo ok > "$out/receipt"
        '';

        formatter = pkgs.nixpkgs-fmt;
      });
}
