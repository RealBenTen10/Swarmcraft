#!/bin/bash

# if we don't guard for this the paths get screwed up
if [ "$(basename "$PWD")" != "server_install" ] ; then
  echo "Please run the installer from within server_install."
  exit 0
fi

read -rp "
!!!READ THE FOLLOWING!!!

This script will install and set up Spigot and PySpigot in the current parent directory ($PWD/../minecraft).
If this is correct, press enter.
If not or if you are uncertain, please (q)uit and consult the swarmcraft docs. " ans < /dev/tty

if [ "$ans" != "" ] ; then
  exit 0
fi

old_dir=$PWD

mkdir -p build
cd build || exit

echo "Downloading BuildTools"
wget -nc https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar # get BuildTools.jar (skip if present)

echo "Installing Spigot"
java -jar BuildTools.jar --rev 1.21.1 # run buildtools, gets us the server jar

# make minecraft dir and copy the jar there
mkdir -p ../../minecraft
mv spigot-1.21.1.jar ../../minecraft

# clean up the build
cd ..
rm -rf build

# switch to install dir
cd ../minecraft || exit
# agree to the eula
read -rp "Press enter to agree to the minecraft EULA (https://aka.ms/MinecraftEULA) (q to quit) " ans < /dev/tty
if [ "$ans" != "" ] ; then
  exit 0
fi
echo "# EULA agreement (https://aka.ms/MinecraftEULA)
eula=true
" > eula.txt

echo "Copying plugin scripts"
# create plugins folder
cp -r ../server_install/plugins .
cd "plugins" || exit
echo "Installing plugins"
wget -nc https://github.com/magicmq/pyspigot/releases/download/v0.8.0/pyspigot-bukkit-0.8.0.jar
cd ..

# this config disables structure generation and forces flat worlds
echo "Copying server config"
cp ../server_install/server.properties .

# server.py is the interface for controlling the server from python
echo "Copying server control script"
cp ../server_install/server.py .

cd "$old_dir" || exit

echo "Done!"
