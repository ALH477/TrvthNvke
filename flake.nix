{
  description = "Truthgate — DeMoD LLC / ALH477. Importable flake for claim-verified READMEs.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      overlay = final: prev: {
        truthgate = final.callPackage ./nix/package.nix {
          src = self;
          version = "0.3.0";
        };
      };
    in
    (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };
      in {
        packages.truthgate = pkgs.truthgate;
        packages.default = pkgs.truthgate;

        apps.truthgate = {
          type = "app";
          program = "${pkgs.truthgate}/bin/truthgate";
        };
        apps.mcp = {
          type = "app";
          program = "${pkgs.truthgate}/bin/truthgate-mcp";
        };
        apps.default = self.apps.${system}.truthgate;

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.truthgate pkgs.python3 pkgs.git ];
          shellHook = ''
            export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
            echo "DeMoD Truthgate $(truthgate --version | cut -d' ' -f2)"
          '';
        };

        formatter = pkgs.nixpkgs-fmt;
      }))
    // {
      overlays.default = overlay;
      nixosModules.default = import ./nix/module.nix;
      nixosModules.truthgate = self.nixosModules.default;

      templates.default = {
        path = ./templates/consumer;
        description = "Import github:ALH477/truthgate into a DeMoD repository";
      };
      templates.consumer = self.templates.default;
    };
}
