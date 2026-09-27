{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.demod.trvthnvke;
in
{
  options.demod.trvthnvke = {
    enable = lib.mkEnableOption "DeMoD TrvthNvke CLI and MCP on this system";
    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.trvthnvke;
      description = "TrvthNvke package to install.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];
  };
}
