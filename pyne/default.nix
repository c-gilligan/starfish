{ lib
, stdenv
, buildPythonPackage
, fetchFromGitHub
, fetchurl
, python
, cmake
, cython
, gfortran
, which
, blas
, hdf5
, lapack
, numpy
, progress
, scipy
, tables
, fixDarwinDylibNames
,
}:
buildPythonPackage rec {
  pname = "pyne";
  version = "unstable-2023-04-19";
  format = "other";

  src = fetchFromGitHub {
    owner = "pyne";
    repo = "pyne";
    rev = "d362173c381128df7dd8ead59f0ef49909e57ef7";
    hash = "sha256-SvGFMgxwCDqKx4YKono6IZuUJyPolKd30Dc++FdEo/Y=";
  };

  patches = [ ./0000-disable-asm-downloads.patch ];

  nativeBuildInputs = [ cmake cython gfortran which ]
      ++ (lib.optional stdenv.isDarwin fixDarwinDylibNames);
  buildInputs = [ blas hdf5 lapack ];
  propagatedBuildInputs = [ numpy progress scipy tables ];

  dontUseCmakeConfigure = true;

  buildPhase =
    let
      fetchPyneData = file: hash:
        fetchurl {
          url = "https://github.com/pyne/data/raw/master/${file}";
          inherit hash;
        };
      decayTar =
        fetchPyneData "decay.tar.gz"
          "sha256-qhqmnLhGhXMesjTARsVvkWegvMlobM1UN/Yhhqyb1EE=";
      cramTar =
        fetchPyneData "cram.tar.gz"
          "sha256-XqFEMiYjR4fguO9/HUycsKaEa52gC8hDVXBRrXTkovU=";
      prebuiltNucData =
        fetchPyneData "prebuilt_nuc_data.h5"
          "sha256-d6j72m2z7RVHZvSnwTRlG6cQ9S01ME8ORW3G9+emmTY=";
    in
    ''
      runHook preBuild

      cp ${decayTar} src/decay.tar.gz
      cp ${cramTar} src/cram.tar.gz

      python setup.py install -j $NIX_BUILD_CORES \
        --slow --build-type release --prefix $out

      cp ${prebuiltNucData} \
        $out/${python.sitePackages}/pyne/nuc_data.h5

      runHook postBuild
    '';

  #pythonImportsCheck = [ "pyne" "pyne.data" ];

  meta = with lib; {
    description = "PyNE: The Nuclear Engineering Toolkit";
    homepage = "https://github.com/pyne/pyne";
    changelog = "https://github.com/pyne/pyne/blob/${src.rev}/CHANGELOG.rst";
    license = with licenses; [ free ];
  };
}
