{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.demod.truthgate;
in
{
  options.demod.truthgate = {
    enable = lib.mkEnableOption "DeMoD Truthgate CLI and MCP on this system";
    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.truthgate;
      description = "Truthgate package to install.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];
  };
}
