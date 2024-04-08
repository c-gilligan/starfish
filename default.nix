{ writeShellScriptBin, python310, runCommand }:

let
  python = (python310.override { x11Support = true; }); # for Tkinter

  pythonWithPackages = python.withPackages (pkgs:
    with pkgs; [
      (callPackage ./openmc { })
      (callPackage ./pyne { })
      numpy
      parsedatetime
      scipy
      tkinter
    ]);

  starfish = runCommand "ir.py" { } ''
    cp ${./ir.py} $out
    ${python}/bin/2to3 --write $out
    substituteInPlace $out --replace '"air_gamma.csv"' '"${./air_gamma.csv}"'
  '';

in
writeShellScriptBin "starfish" ''
  exec ${pythonWithPackages}/bin/python ${starfish}
''
