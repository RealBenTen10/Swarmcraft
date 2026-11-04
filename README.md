Swarmcraft

This is a framework for minecraft-based multi-agent simulations.
Users can create agents and run experiments in custom environments.
Logging tools are also included, as well as a suite of tools for behavior-tree-based agent control.

Installation/Setup

This section describes the process to install and configure the framework for the Swarmcraft project on an Ubuntu 24 environment with the specified software dependencies.

Cloning the repository is already half the battle. In case you haven't done so yet:

git clone https://gitlab.inf.uni-konstanz.de/benedict.da-silva-araujo-finsterwalder/SwarmcraftProject.git

It is recommended to use PyCharm as the IDE. Visual Studio Code may lead to incorrect module resolution because the current working directory is set to SwarmcraftProject instead of SwarmcraftProject/swarmcraft when running the SwarmcraftProject/swarmcraft/main.py file.

Requirements

For the rest of the installation process, the following tools and versions are required:

Operating System: Ubuntu 24.04.4 LTS

Java SDK: Version 21.0.10

Python: Version 3.12.3 or higher

Node.js: Version 22.14.0

npm: Version 11.3.0

Minecraft launcher (e.g. https://atlauncher.com/downloads) with Minecraft 1.21.1

Python and Node Setup

Several additional libraries are required. Navigate to the repository root directory and set up your Python virtual environment and dependencies.

Python virtual environment setup:

python3 -m venv .venv

source .venv/bin/activate

Install required Python packages:

pip install -r swarmcraft/requirements.txt

The required Python packages include:

javascript==1!1.2.6

numpy==2.3.3

pandas==2.3.2

python-dateutil==2.9.0.post0

pytz==2025.2

shortuuid==1.0.13

six==1.17.0

tzdata==2025.2

Ensure Node.js and npm versions are aligned:

node -v (should display v22.14.0)

npm -v (should display 11.3.0)

If needed, update Node.js using Node Version Manager (nvm):

nvm install 22.14.0

nvm use 22.14.0