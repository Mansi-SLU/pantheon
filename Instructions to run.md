Install Dependencies - 
sudo apt update
sudo apt install -y git python3 python3-pip build-essential cmake \
libssl-dev pkg-config libpcap-dev mahimahi iproute2 iputils-ping \
net-tools gnuplot autoconf automake apache2 \
libxcb-present-dev libpangocairo-1.0-dev libpango1.0-dev libcairo2-dev


Install Pantheon Dependencies - 
chmod +x tools/install_deps.sh
./tools/install_deps.sh

Test Schemes with Pantheon - 
python3 tests/test_schemes.py --schemes "cubic fillp vegas"

Install Mahimahi - 
cd mahimahi
./autogen.sh
./configure
make
sudo make install

Enable Packet Forwarding (Required by Mahimahi) - 
sudo sysctl -w net.ipv4.ip_forward=1

Test Mahimahi - 
mm-delay 100 mm-link traces/50mbps.trace traces/50mbps.trace -- bash

Run Custom Experiments - 
python3 /home/slu/pantheon/src/experiments.py

This will:
Run all schemes under each defined network profile
Save results and logs under results/profile/scheme/
Generate plots under results/graphs/
