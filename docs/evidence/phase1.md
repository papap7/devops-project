# Phase 1 evidence: self-configuring server

**Date:** 2026-11-03 | **VM:** devbox (Multipass, Ubuntu 24.04, arm64) | **Host:** Mac (Apple Silicon)
**Built from:** `cloud-init.yaml` at commit `29923b3`

---

## 1. cloud-init.yaml passes the schema check
**Claim:** the file starts with `#cloud-config` and the config the VM used is valid.
**Command:**
```
sudo cloud-init schema --system
```
**Output:**
```
Found cloud-config data types: user-data, vendor-data, network-config

1. user-data at /var/lib/cloud/instances/devbox/cloud-config.txt:
  Valid schema user-data

2. vendor-data at /var/lib/cloud/instances/devbox/vendor-cloud-config.txt:
Cloud config schema deprecations: system_info:  Deprecated in version 24.2. System and/or distro specific settings. This is not intended to be overridden by user-data or vendor-data.
  Valid schema vendor-data

3. network-config at /var/lib/cloud/instances/devbox/network-config.json:
  Valid schema network-config
```
**Notes:** Run inside the VM. The deprecation warning is under vendor-data (the platform's config), not in my cloud-init.yaml; user-data is valid.

## 2. VM launched with --cloud-init and first boot finished cleanly
**Claim:** cloud-init finished with no errors.
**Command:**
```
time (multipass launch noble --name devbox --cpus 2 --memory 2G --disk 15G --cloud-init ~/Documents/Projects/devops-project/cloud-init.yaml && multipass exec devbox -- cloud-init status --wait --long)
multipass list
```
**Output:**
```
Launched: devbox
status: done
extended_status: done
boot_status_code: enabled-by-generator
last_update: Thu, 01 Jan 1970 00:00:43 +0000
detail: DataSourceNoCloud [seed=/dev/vda]
errors: []
recoverable_errors: {}
( multipass launch noble --name devbox --cpus 2 --memory 2G --disk 15G   &&  )  0.03s user 0.01s system 0% cpu 51.932 total

Name                    State             IPv4             Image
devbox                  Running           192.168.252.7    Ubuntu 24.04 LTS
                                          172.17.0.1
```
**Notes:** First boot finished with no errors. An earlier launch failed in the runcmd script; see [incident #1](../incident-log.md).

## 3. Docker Engine and Compose v2 installed
**Claim:** both are installed, and Compose is the v2 plugin (`docker compose`).
**Command:**
```
docker --version
docker compose version
```
**Output:**
```
Docker version 29.9.2, build a82e528
Docker Compose version v5.7.0
```
**Notes:** Run inside the VM. Docker is installed from Docker's own apt repository (set up in cloud-init.yaml), not from Ubuntu's repo. Compose is the v2 plugin, so the command is `docker compose` with a space.

## 4. SSH login with my own key
**Claim:** I log in as `ubuntu` with the project key, and password login is disabled for that account.
**Command:**
```
ssh ubuntu@192.168.252.7 -i ~/.ssh/id_devbox
passwd -S
```
**Output:**
```
Welcome to Ubuntu 24.04.5 LTS (GNU/Linux 6.8.0-147-generic aarch64)

...
  IPv4 address for enp0s1: 192.168.252.7
...
Last login: Tue Nov  3 09:40:38 2026 from 192.168.252.1
ubuntu@devbox:~$

ubuntu L 2026-11-03 0 99999 7 -1
```
**Notes:** `L` means the password is locked (`lock_passwd: true` in cloud-init.yaml), so the key is the only way in over SSH. The date in `passwd -S` is the password's last-change field. The passphrase is on the key on my Mac and is not the VM account's password. The private key is not in the repo. Welcome text trimmed.

## 5. docker group and hello-world without sudo
**Claim:** `ubuntu` is in the `docker` group and `hello-world` runs without `sudo` in a fresh login.
**Command:**
```
id
docker run hello-world
```
**Output:**
```
uid=1000(ubuntu) gid=1001(ubuntu) groups=1001(ubuntu),4(adm),24(cdrom),27(sudo),30(dip),104(lxd),1000(docker)

Unable to find image 'hello-world:latest' locally
latest: Pulling from library/hello-world
58dee6a49ef1: Pull complete 
c3bdf82c34d1: Download complete 
Digest: sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef
Status: Downloaded newer image for hello-world:latest

Hello from Docker!
...
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (arm64v8)
...
```
**Notes:** Run in a new SSH session, because group changes only apply to new logins. The image pulled is arm64, matching the VM. Output trimmed after "Hello from Docker!".

## 6. Docker starts on boot
**Claim:** the Docker service is enabled.
**Command:**
```
systemctl is-enabled docker
systemctl status docker
```
**Output:**
```
enabled

● docker.service - Docker Application Container Engine
     Loaded: loaded (/usr/lib/systemd/system/docker.service; enabled; preset: enabled)
     Active: active (running) since Tue 2026-11-03 09:40:04 PST; 11min ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 7966 (dockerd)
      Tasks: 11
     Memory: 32.4M (peak: 35.0M)
        CPU: 434ms
     CGroup: /system.slice/docker.service
             └─7966 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock

Nov 03 09:40:04 devbox dockerd[7966]: time="2026-11-03T09:40:04.162812751+08:00" level=info ms>
Nov 03 09:40:04 devbox dockerd[7966]: time="2026-11-03T09:40:04.162855751+08:00" level=info ms>
Nov 03 09:40:04 devbox dockerd[7966]: time="2026-11-03T09:40:04.217332959+08:00" level=info ms>
Nov 03 09:40:04 devbox dockerd[7966]: time="2026-11-03T09:40:04.218636376+08:00" level=info ms>
Nov 03 09:40:04 devbox dockerd[7966]: time="2026-11-03T09:40:04.218664792+08:00" level=info ms>
Nov 03 09:40:04 devbox systemd[1]: Started docker.service - Docker Application Container Engin>
Nov 03 09:40:50 devbox dockerd[7966]: time="2026-11-03T09:40:50.438455256+08:00" level=info ms>
Nov 03 09:40:50 devbox dockerd[7966]: time="2026-11-03T09:40:50.537422835+08:00" level=info ms>
Nov 03 09:40:50 devbox dockerd[7966]: time="2026-11-03T09:40:50.552606476+08:00" level=info ms>
Nov 03 09:49:41 devbox dockerd[7966]: time="2026-11-03T09:49:41.458866174+08:00" level=info ms>
```
**Notes:** Nothing in cloud-init.yaml enables the service; the Docker package does. `TriggeredBy: docker.socket` shows the socket unit can also start it. Journal output is the last lines systemctl status shows, cut to terminal width.

## 7. UFW
**Claim:** incoming traffic is denied by default; SSH is allowed only from my Mac; port 80 is open.
**Command:**
```
sudo ufw status verbose
```
**Output:**
```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    192.168.252.1              # Macbook SSH
80/tcp                     ALLOW IN    Anywhere                  
80/tcp (v6)                ALLOW IN    Anywhere (v6)
```
**Notes:** SSH is allowed only from 192.168.252.1, the VM's default gateway, which is my Mac on the Multipass network. The file doesn't set the default policy; UFW's own default is deny incoming. Ports published by Docker can bypass UFW; I'll handle that in Phase 2.

## 8. Rebuild from zero
**Claim:** the VM rebuilds from the file alone.
**Time from launch to cloud-init done:** 52 s (measured with shell `time` over launch + `cloud-init status --wait`)
**Time from launch to working hello-world:** 1 min 37 s (stopwatch; includes finding the IP, SSH login with passphrase, and the image pull)
**Notes:** Built from commit 29923b3. Ubuntu image already cached. Heavy browser tabs closed, memory pressure green.

## 9. Commit
**Link:** https://github.com/papap7/devops-project/commit/29923b3
