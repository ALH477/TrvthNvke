{
  description = "Example DeMoD repository importing Truthgate from github:ALH477/truthgate";

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
          packages = [ pkgs.truthgate pkgs.python3 pkgs.git ];
          shellHook = ''
            echo "Truthgate ready: $(command -v truthgate)"
            echo "Gate this tree with: truthgate verify --fail"
          '';
        };

        checks.readme = pkgs.runCommand "truthgate-readme" {
          nativeBuildInputs = [ pkgs.truthgate ];
          src = self;
        } ''
          cp -r "$src"/. .
          chmod -R u+w .
          truthgate verify --fail
          mkdir -p "$out"
          echo ok > "$out/receipt"
        '';

        formatter = pkgs.nixpkgs-fmt;
      });
}
