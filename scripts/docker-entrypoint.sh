#!/bin/bash
set -euo pipefail

# =============================================================================
# MagesticAI Docker Entrypoint
# =============================================================================
# Runs as root to set up iptables firewall blocking LAN access,
# then drops to the magesticai user via gosu.
# =============================================================================

GATEWAY_IP="${CONTAINER_GATEWAY:-<gateway>}"
BLOCKED_RANGES="${CONTAINER_BLOCKED_RANGES:-10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"
ENABLE_LAN_FIREWALL="${CONTAINER_LAN_FIREWALL:-true}"

if [ "$ENABLE_LAN_FIREWALL" = "true" ]; then
    echo "[entrypoint] Setting up LAN firewall..."

    iptables -F OUTPUT

    # Allow loopback + established return traffic
    iptables -A OUTPUT -o lo -j ACCEPT
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # Allow DNS + ICMP to gateway (needed for internet routing)
    iptables -A OUTPUT -d "$GATEWAY_IP" -p udp --dport 53 -j ACCEPT
    iptables -A OUTPUT -d "$GATEWAY_IP" -p tcp --dport 53 -j ACCEPT
    iptables -A OUTPUT -d "$GATEWAY_IP" -p icmp -j ACCEPT

    # Block all RFC 1918 private ranges
    IFS=',' read -ra RANGES <<< "$BLOCKED_RANGES"
    for range in "${RANGES[@]}"; do
        iptables -A OUTPUT -d "$range" -j DROP
        echo "[entrypoint]   Blocked: $range"
    done

    echo "[entrypoint] LAN firewall active."
fi

# Drop to non-root user (gosu handles signals properly for PID 1)
exec gosu magesticai "$@"
