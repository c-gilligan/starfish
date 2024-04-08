{ lib
, buildPythonPackage
, fetchFromGitHub
, cython
, numpy
, setuptools
, wheel
, h5py
, ipython
, lxml
, matplotlib
, pandas
, scipy
, uncertainties
,
}:
buildPythonPackage rec {
  pname = "openmc";
  version = "0.13.3";
  format = "pyproject";

  src = fetchFromGitHub {
    owner = "openmc-dev";
    repo = "openmc";
    rev = "v${version}";
    hash = "sha256-PLp+WXiCoAe+Nk3MOaA8AMZ6GPl1zwDhHY0wFdPlBeg=";
  };

  nativeBuildInputs = [ cython numpy setuptools wheel ];

  propagatedBuildInputs = [ h5py ipython lxml matplotlib pandas scipy uncertainties ];

  pythonImportsCheck = [ "openmc" ];

  meta = with lib; {
    description = "OpenMC Monte Carlo Code";
    homepage = "https://github.com/openmc-dev/openmc";
    license = licenses.mit;
  };
}
