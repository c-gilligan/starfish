{
  description = "Starfish (irradiation planning tool)";

  outputs = { self, nixpkgs }:
    let
      forAllSystems = gen:
        nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed
          (system: gen nixpkgs.legacyPackages.${system});
    in
    {
      # Note: only tested on x86_64-linux; other platforms might not work!
      packages = forAllSystems (pkgs: rec {
        starfish = pkgs.callPackage ./. { };
        default = starfish;
      });
      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);
    };
}
