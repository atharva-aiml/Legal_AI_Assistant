#!/usr/bin/env bash
# One-time preparation of a fresh Oracle Cloud Ubuntu VM (24.04, Ampere A1).
# Run as the default `ubuntu` user:  bash deploy/setup-vm.sh
set -euo pipefail

echo "==> Installing Docker Engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"

echo "==> Opening ports 80/443 in the VM's own firewall"
# Oracle's Ubuntu images ship iptables rules that REJECT everything except SSH,
# independently of the cloud Security List — both must allow 80/443.
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -p tcp --dport "$port" -m state --state NEW -j ACCEPT
  fi
done
sudo netfilter-persistent save

echo "==> Adding a 2 GB swap file (headroom during image builds)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo
echo "Done. Log out and back in (so the docker group applies), then:"
echo "  cp deploy/.env.example deploy/.env && nano deploy/.env"
echo "  bash deploy/deploy.sh"
