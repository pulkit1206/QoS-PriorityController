#!/bin/bash
# Run this inside Mininet CLI using:
# mininet> sh bash tests/traffic_test.sh

echo "=== Starting QoS Traffic Test ==="

# Start iperf server on h3
echo "Starting iperf server on h3..."
mx h3 iperf -s &

sleep 1

echo ""
echo "=== Test 1: VoIP (UDP high priority) ==="
mx h1 iperf -c 10.0.0.3 -u -b 5m -t 5

echo ""
echo "=== Test 2: HTTP (TCP medium priority) ==="
mx h2 iperf -c 10.0.0.3 -b 5m -t 5

echo ""
echo "=== Test 3: Competing traffic ==="
echo "Running VoIP and FTP simultaneously..."
mx h1 iperf -c 10.0.0.3 -u -b 5m -t 10 &
mx h2 iperf -c 10.0.0.3 -b 5m -t 10

echo ""
echo "=== Test Complete ==="
kill %1 2>/dev/null
