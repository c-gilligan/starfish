# starfish
Starfish is the software used by the Reed Research Reactor to calculate neutron activation of samples to be irradiated. 

## Current State 
Starfish was made with Python 2 and is wildly outdated. Prior to 2023, it only ran on the RRR lab computer, and was not able to run anywhere else. 

Efforts by [Connor Gilligan](https://github.com/c-gilligan/) and friends have made it possible to run via hacky patches using the Nix package manager. 

## How to run 
1. Install Nix according to its [install instructions](https://nix.dev/install-nix).
2. Clone the repository with `git clone https://github.com/c-gilligan/starfish.git`
3. Using a terminal, enter the repository folder and run `nix run --extra-experimental-features nix-command --extra-experimental-features flakes`. It will take a minute or two to build the first time, but will only take a few seconds after that.
4. Select a flux profile (RRR employees: Use rabbit.csv for rabbit. Don't forget to read the SOPs.)

Note: This procedure may require you to first install [PyNE (Python Nuclear Engineering toolkit)](https://github.com/pyne/pyne). If you have an ARM device, such as Apple silicon Macs, PyNE must be compiled with the `--slow` flag, and the compiled dylib file may need to be manually copied into the right place or added to PATH for the OS to find it. 

## Planned Changes 
- Efforts are ongoing to port Starfish to python 3.
- Consideration for whether to rewrite Starfish entirely in another language are ongoing. 
