{
  lib,
  python3,
  stdenvNoCC,
  makeWrapper,
  src,
  version ? "0.4.0",
}:
stdenvNoCC.mkDerivation {
  pname = "trvthnvke";
  inherit version src;

  nativeBuildInputs = [ makeWrapper ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib $out/bin
    cp -r src/trvthnvke $out/lib/trvthnvke
    # pre-0.4.0 name: the shim package, so `python -m truthgate` still resolves
    # for anything that puts $out/lib on PYTHONPATH.
    cp -r src/truthgate $out/lib/truthgate
    makeWrapper ${python3}/bin/python3 $out/bin/trvthnvke \
      --prefix PYTHONPATH : $out/lib \
      --add-flags "-m trvthnvke"
    makeWrapper ${python3}/bin/python3 $out/bin/trvthnvke-mcp \
      --prefix PYTHONPATH : $out/lib \
      --add-flags "-m trvthnvke mcp"
    # Compatibility alias for the pre-0.4.0 command name, matching the
    # `truthgate` console script in pyproject.toml. Same entry point.
    makeWrapper ${python3}/bin/python3 $out/bin/truthgate \
      --prefix PYTHONPATH : $out/lib \
      --add-flags "-m trvthnvke"
    runHook postInstall
  '';

  meta = with lib; {
    description = "Git-enforced, claim-verified READMEs with CI gates and an agent MCP";
    homepage = "https://github.com/ALH477/trvthnvke";
    license = licenses.asl20;
    maintainers = [{
      name = "ALH477";
      github = "ALH477";
    }];
    mainProgram = "trvthnvke";
    platforms = platforms.all;
  };
}
