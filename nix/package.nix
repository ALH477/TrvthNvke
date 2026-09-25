{
  lib,
  python3,
  stdenvNoCC,
  makeWrapper,
  src,
  version ? "0.2.0",
}:
stdenvNoCC.mkDerivation {
  pname = "truthgate";
  inherit version src;

  nativeBuildInputs = [ makeWrapper ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib $out/bin
    cp -r src/truthgate $out/lib/truthgate
    makeWrapper ${python3}/bin/python3 $out/bin/truthgate \
      --prefix PYTHONPATH : $out/lib \
      --add-flags "-m truthgate"
    makeWrapper ${python3}/bin/python3 $out/bin/truthgate-mcp \
      --prefix PYTHONPATH : $out/lib \
      --add-flags "-m truthgate mcp"
    runHook postInstall
  '';

  meta = with lib; {
    description = "Git-enforced, claim-verified READMEs with CI gates and an agent MCP";
    homepage = "https://github.com/ALH477/truthgate";
    license = licenses.asl20;
    maintainers = [{
      name = "ALH477";
      github = "ALH477";
    }];
    platforms = platforms.all;
  };
}
