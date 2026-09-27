{
  description = "TrvthNvke — DeMoD LLC / ALH477. Importable flake for claim-verified READMEs.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      overlay = final: prev: {
        trvthnvke = final.callPackage ./nix/package.nix {
          src = self;
          version = "0.4.0";
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
        packages.trvthnvke = pkgs.trvthnvke;
        packages.default = pkgs.trvthnvke;

        apps.trvthnvke = {
          type = "app";
          program = "${pkgs.trvthnvke}/bin/trvthnvke";
        };
        apps.mcp = {
          type = "app";
          program = "${pkgs.trvthnvke}/bin/trvthnvke-mcp";
        };
        apps.default = self.apps.${system}.trvthnvke;

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.trvthnvke pkgs.python3 pkgs.git ];
          shellHook = ''
            export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
            echo "DeMoD TrvthNvke $(trvthnvke --version | cut -d' ' -f2)"
          '';
        };

        formatter = pkgs.nixpkgs-fmt;
      }))
    // {
      overlays.default = overlay;
      nixosModules.default = import ./nix/module.nix;
      nixosModules.trvthnvke = self.nixosModules.default;

      templates.default = {
        path = ./templates/consumer;
        description = "Import github:ALH477/TrvthNvke into a DeMoD repository";
      };
      templates.consumer = self.templates.default;
    };
}
