# Mininet Network Security Lab

A Mininet-based lab that builds a small routed network, generates baseline traffic, simulates two classic denial-of-service attacks (ICMP flood and TCP SYN flood), and defends against them using `iptables` firewall rules on the router. Traffic is captured with `tcpdump` and analysed in Wireshark, with performance compared across every stage.

This was a **group coursework project** for a Network Security module, themed around network attack and defence. The task was to take a network through a full lifecycle — build it and prove connectivity, establish a traffic benchmark, attack it and measure the damage, defend it with a firewall and measure the recovery, then critically reflect on the results and on each member's role (attacker/victim) in the experiment.

## Project requirements

The coursework was structured as five marked levels totalling 100 marks, evidenced in a report (max 1500 words) or a video demonstration (max 15 minutes), with all group members sharing the same mark:

- **Level 1 — Build a network and test connectivity (20 marks).** Build a network in Mininet (or VMs), draw the topology with every node's IP labelled, and prove reachability between all hosts using `ping`.
- **Level 2 — Generate and analyse traffic (20 marks).** Generate sensible traffic (e.g. with `iperf`), capture it with `tcpdump`/Wireshark, and analyse it at the protocol, packet, and flow level — measuring throughput, delay, and packet loss to establish a benchmark for later comparison.
- **Level 3 — Network attack(s) (25 marks).** With normal traffic running, launch one or more attacks (ICMP flood, TCP SYN flood, IP spoofing, etc., e.g. via `hping3`) and analyse their impact against the Level 2 baseline.
- **Level 4 — Network defence (25 marks).** Configure a firewall (`iptables`) to mitigate the attacks, re-run the normal and attack traffic, and demonstrate effectiveness by comparing performance across Levels 2, 3, and 4.
- **Level 5 — Critical evaluation and reflection (10 marks).** Critically evaluate the work on both technical and social grounds, with each group member stating their role and contribution.

This repository contains our implementation of Levels 1–4 (the Mininet network and the commands that drive each level) together with the full written report, which also covers the Level 5 evaluation.

## Topology

A routed "extended star": three client PCs sit on a LAN behind a switch, the switch connects to a router, and the router connects to a server that acts as "The Internet".

```
  PC1 (192.168.0.2)
  PC2 (192.168.0.3) ── Switch1 ── Router1 ── Server (192.168.2.100)
  PC3 (192.168.0.4)              eth0: 192.168.0.1   "The-Internet"
                                 eth1: 192.168.2.1
```

| Node    | Interface / Role        | IP address        |
|---------|-------------------------|-------------------|
| PC1     | LAN client              | 192.168.0.2/24    |
| PC2     | LAN client              | 192.168.0.3/24    |
| PC3     | LAN client              | 192.168.0.4/24    |
| Router1 | LAN gateway (eth0)      | 192.168.0.1/24    |
| Router1 | Server-facing (eth1)    | 192.168.2.1/24    |
| Server  | "The-Internet" target   | 192.168.2.100/24  |

The LAN clients use `192.168.0.1` as their default gateway; the server routes back via `192.168.2.1`. IP forwarding is enabled on Router1 and NAT (MASQUERADE) is configured so the LAN can reach the host's uplink.

## Files

| File | Description |
|------|-------------|
| `coursework.py` | Mininet Python script that builds the topology, configures the router (IP forwarding, addressing, NAT) and drops into the Mininet CLI. |
| `coursework.mn` | MiniEdit topology file (the same network, openable in MiniEdit's GUI). |
| `mininet_network_security_lab.pdf` | Full lab report covering all five levels with figures and analysis. |

## Requirements

- A Linux environment with [Mininet](http://mininet.org/) installed (the lab was developed on Ubuntu 24.04).
- Root privileges (Mininet must run as `sudo`).
- The following tools available on the hosts: `iperf`, `hping3`, `tcpdump`, `iptables`.
- Wireshark for offline analysis of the captured `.pcap` files.

Install the extra tools if needed:

```bash
sudo apt update
sudo apt install mininet iperf hping3 tcpdump wireshark
```

> **Note:** `coursework.py` configures NAT against a host uplink interface named `enp0s5` and a gateway of `10.211.55.1`. Edit those two values near the bottom of the script to match your own machine before running, or remove the NAT lines if you don't need outbound internet access.

## Running the lab

Launch the network:

```bash
sudo python3 coursework.py
```

You should see the build steps print out and then land at the `mininet>` prompt.

### Level 1 — Connectivity test

Verify end-to-end reachability from the CLI:

```text
mininet> PC1 ping PC2 -c 3
mininet> PC1 ping PC3 -c 3
mininet> PC1 ping Router1 -c 3
mininet> PC1 ping Server -c 3
```

All pings should return 0% packet loss.

### Level 2 — Baseline traffic generation and capture

Start a capture on the server interface, then drive TCP and UDP throughput with iPerf:

```text
mininet> Server tcpdump -i Server-eth0 -w /tmp/baseline_traffic.pcap &

# TCP test
mininet> Server iperf -s -p 5001 &
mininet> PC1 iperf -c 192.168.2.100 -p 5001 -t 30

# UDP test
mininet> Server iperf -s -u -p 5002 &
mininet> PC1 iperf -c 192.168.2.100 -u -p 5002 -b 10M -t 30

mininet> Server kill %tcpdump
```

Open the capture for analysis:

```bash
sudo wireshark /tmp/baseline_traffic.pcap
```

Useful Wireshark views: **Statistics → Protocol Hierarchy**, **Statistics → Conversations** (Ethernet / IPv4 / TCP / UDP tabs), and **Statistics → I/O Graph**.

### Level 3 — Simulated attacks

Open separate terminals for each node, then set the server up to listen and capture:

```text
mininet> xterm Server PC1 PC2 PC3

Server> iperf -s -p 5001 &
Server> iperf -s -u -p 5002 &
Server> tcpdump -i Server-eth0 -w /tmp/attack_icmp.pcap &
```

**Attack 1 — ICMP flood.** While PC1 runs normal TCP traffic, PC2 floods the server with ICMP echo requests:

```text
PC1> iperf -c 192.168.2.100 -p 5001 -t 120
PC2> hping3 --icmp --flood 192.168.2.100      # Ctrl+C after ~30 s
```

**Attack 2 — TCP SYN flood.** Capture to a new file, run baseline traffic, then flood the server's TCP port from PC3:

```text
Server> tcpdump -U -i Server-eth0 -w /tmp/attack_syn.pcap &
PC1> iperf -c 192.168.2.100 -p 5001 -t 120
PC3> hping3 -S --flood -p 5001 192.168.2.100  # Ctrl+C after ~30 s

# Optional: SYN flood with spoofed source addresses
PC3> hping3 -S --flood -p 5001 --rand-source 192.168.2.100
```

### Level 4 — Defence with an iptables firewall

Firewall rules are applied on **Router1**, which forwards all LAN↔server traffic.

**Defend against the ICMP flood** with rate limiting — allow a small burst, then drop the rest:

```text
mininet> Router1 iptables -A FORWARD -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 4 -j ACCEPT
mininet> Router1 iptables -A FORWARD -p icmp --icmp-type echo-request -j DROP
mininet> Router1 iptables -L -n -v
```

Re-run the ICMP attack from Level 3 and confirm the dropped-packet counters climb while the server stays reachable.

**Defend against the SYN flood** by dropping forwarded traffic from the attacking host to the server:

```text
mininet> Router1 iptables -A FORWARD -s 192.168.0.4 -d 192.168.2.100 -j DROP
mininet> Router1 iptables -L -n -v
```

Re-run the SYN attack and confirm PC1's legitimate traffic still completes while the attacker's packets are dropped at the router.

**Reset the firewall** between experiments:

```text
mininet> Router1 iptables -F
```

### Shutting down

```text
mininet> exit
sudo mn -c      # clean up any leftover Mininet state
```

## Results summary

| Metric | Level 2: Baseline | Level 3: Attack | Level 4: Defence |
|--------|-------------------|-----------------|------------------|
| Protocol mix | TCP dominant, small UDP | ICMP/SYN rises sharply | TCP dominant again |
| Packet volume | Moderate | Large spike during flood | Reduced at the server |
| Throughput | Stable | Degraded, bursty | Restored near baseline |
| Attacker traffic at server | n/a | Reaches server | ~0% (dropped at router) |

The lab demonstrates that targeted, rule-based filtering at a strategic point (the router) effectively mitigates both flood types. As a controlled simulation it does not capture adaptive real-world attackers, so static rules alone would not generalise to production networks without additional mechanisms — a point developed further in the Level 5 critical evaluation.

## Troubleshooting

- **`listener bind failed: Address already in use`** — a previous iPerf server is still running. Kill it or run `sudo mn -c` and relaunch.
- **NAT / no internet from the LAN** — update the uplink interface (`enp0s5`) and gateway (`10.211.55.1`) in `coursework.py` to match your host.
- **Interface name too long** — the server host is named `Server` (not `The-Internet`) to stay within Linux's 15-character interface-name limit.
- **Stale state after a crash** — always run `sudo mn -c` before starting again.