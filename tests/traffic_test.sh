#!/bin/bash
echo "=== QoS Traffic Test ==="

echo "Test 1: VoIP (UDP - should be fastest)"
h1 iperf -c 10.0.0.3 -u -b 5m -t 5

echo "Test 2: HTTP (TCP port 80 - medium)"
h2 iperf -c 10.0.0.3 -p 80 -t 5

echo "Test 3: FTP (TCP port 21 - lowest)"
h2 iperf -c 10.0.0.3 -p 21 -t 5

echo "Test 4: Competing traffic"
h1 iperf -c 10.0.0.3 -u -b 5m -t 10 &
h2 iperf -c 10.0.0.3 -t 10