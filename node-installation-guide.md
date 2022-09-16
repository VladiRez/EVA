# Guide zum Aufsetzen von Nodes im Docker-Swarm Cluster (VirtualBox VM)

1. VMs erstellen, min. 1GB RAM
2. Debian 11.4 Bullseye installieren, keine Desktop Environment installieren dafür einen SSH Server.

3. In den VirtualBox Einstellungen:
> File - Host Network Manager - create - DHCP Server enable
> Jede VM: Network - Neuer Host-only adapter

4. In die VMs einloggen, dann:
> su
Wenn ssh server nicht vorinstalliert:
> sudo apt install openssh-server
> sudo systemctl status ssh

5. Netzwerk Interfaces einstellen
> vi /etc/network/interfaces
Settings from primary network interface kopieren:
> auto enp0s8
> iface enp0s8 inet dhcp

6. Text-Editor installieren
> apt install sudo neovim

7. Insecure Registry hinzufügen, falls diese kein SSL Zertifikat hat: 
> nvim /etc/docker/daemon.json
>  {
>    "insecure-registries" : [ "hostname.cloudapp.net:5000" ]
>  }

8. Reboot

9. Docker auf allen Maschinen installieren:
https://docs.docker.com/engine/install/debian/

10. Portainer installieren:
https://docs.portainer.io/v/ce-2.6/start/install/server/swarm/linux 

11. Registry aufsetzen:
Service in Portainer erstellen für folgendes Image:
https://hub.docker.com/_/registry/
