Debian 11.4 Bullseye, keine DE für worker, dafür ssh server

VirtualBox:
> File - Host Network Manager - create - DHCP Server enable
> Jede VM: Network - Neuer Host-only adapter

> su
Wenn ssh server nicht vorinstalliert:
> sudo apt install openssh-server
> sudo systemctl status ssh

> vi /etc/network/interfaces
Settings from primary network interface kopieren:
> auto enp0s8
> iface enp0s8 inet dhcp

> apt install sudo neovim

> nvim /etc/docker/daemon.json
>  {
>    "insecure-registries" : [ "hostname.cloudapp.net:5000" ]
>  }


Reboot

Optional: Guest Additions installieren:

https://linuxize.com/post/how-to-install-virtualbox-guest-additions-on-debian-10/

## docker install:
https://docs.docker.com/engine/install/debian/

## portainer install:
https://docs.portainer.io/v/ce-2.6/start/install/server/swarm/linux 

## Registry:
Service in Portainer erstellen
https://hub.docker.com/_/registry/
