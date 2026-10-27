---
layout: page
permalink: /research/
title: research
description: Mixed-signal ICs and system architectures for neural interfaces, FPGA-based sensor systems, and high-speed wireline links.
nav: true
nav_order: 1
---

<div class="bics-research" markdown="0">
  <p class="rf-intro">We study mixed-signal integrated circuits and the system architectures around them, where sensing front-ends, data conversion, clocking, and digital processing are treated as one design problem. Current work follows three connected directions, pursued through university research and industry-linked sensor and readout projects.</p>
  <nav class="rf-toc" aria-label="Research topics">
    <ul>
      <li><a href="#neural-interfaces">Neural Interfaces</a></li>
      <li><a href="#fpga-systems">FPGA-based Systems</a></li>
      <li><a href="#high-speed-interfaces">High-speed Interfaces</a></li>
    </ul>
  </nav>
  <!-- Neural interfaces: text left, closed-loop SVG right -->
  <section class="rf-section" id="neural-interfaces" aria-labelledby="neural-interfaces-heading">
    <h2 id="neural-interfaces-heading">Neural Interfaces</h2>
    <div class="rf-split">
      <div class="rf-text">
        <p>An implantable neural interface must record microvolt-level signals across many channels and deliver precise stimulation, all within tight power, area, and wireless-bandwidth budgets. We study these trade-offs at the architecture level, from acquisition and on-chip data reduction to stimulation and wireless links. Within the Brain-to-X research direction of Korea's Alchemist Project, we contribute circuit-level work as one member of a multi-institution team.</p>
        <ul class="rf-focus">
          <li>Low-noise recording front-ends and ADCs with spike-aware on-chip data reduction</li>
          <li>Programmable multi-site current stimulation with charge-balanced pulse delivery</li>
          <li>Wireless power delivery and bidirectional data links matched to the implant's energy budget</li>
        </ul>

      </div>
      <figure class="rf-figure">
        <svg class="rf-svg" viewBox="0 0 320 304" role="img" aria-labelledby="rf-neural-title rf-neural-desc">
          <title id="rf-neural-title">Conceptual closed-loop neural interface</title>
          <desc id="rf-neural-desc">Signals from the electrodes pass to a recording front-end and then to a wireless link. An external unit supplies wireless power and exchanges data and stimulation commands with the implant. The stimulator delivers current back to the electrodes.</desc>
          <defs>
            <marker id="rf-neural-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
              <path class="rf-head" d="M0,0 L10,5 L0,10 z"/>
            </marker>
          </defs>
          <rect class="rf-box rf-box--context" x="8" y="8" width="304" height="40" rx="6" fill="none"/>
          <text class="rf-label" x="160" y="33">Electrodes on neural tissue</text>
          <rect class="rf-box" x="8" y="92" width="140" height="56" rx="6" fill="none"/>
          <text class="rf-label" x="78" y="116">Recording</text>
          <text class="rf-sub" x="78" y="134">amplifier + ADC</text>
          <rect class="rf-box" x="172" y="92" width="140" height="56" rx="6" fill="none"/>
          <text class="rf-label" x="242" y="116">Stimulator</text>
          <text class="rf-sub" x="242" y="134">current pulses</text>
          <rect class="rf-box" x="8" y="192" width="304" height="48" rx="6" fill="none"/>
          <text class="rf-label" x="160" y="213">Wireless link</text>
          <text class="rf-sub" x="160" y="231">wireless power + data</text>
          <rect class="rf-box rf-box--context" x="80" y="268" width="160" height="32" rx="6" fill="none"/>
          <text class="rf-label" x="160" y="289">External unit</text>
          <path class="rf-line" d="M78 48 V91" fill="none" marker-end="url(#rf-neural-head)"/>
          <path class="rf-line" d="M78 148 V191" fill="none" marker-end="url(#rf-neural-head)"/>
          <path class="rf-line" d="M242 192 V149" fill="none" marker-end="url(#rf-neural-head)"/>
          <path class="rf-line" d="M242 92 V49" fill="none" marker-end="url(#rf-neural-head)"/>
          <path class="rf-line" d="M160 241 V267" fill="none" marker-start="url(#rf-neural-head)" marker-end="url(#rf-neural-head)"/>
        </svg>
        <figcaption>Conceptual closed-loop neural interface. Solid blocks are the circuit functions we design; dashed blocks are the surrounding system.</figcaption>
      </figure>
    </div>
    <div class="rf-paper-group">
        <h3 class="rf-papers-title">Selected papers</h3>
        <ul class="rf-papers">
          <li><a href="{{ '/publications/' | relative_url }}#kang2026neurostim">A Flying Push-Pull Current Neurostimulator With Body-Coupled Powering and Full-Duplex Communication for Multi-Site Stimulation</a><span class="rf-venue">IEEE JSSC, 2026</span></li>
          <li><a href="{{ '/publications/' | relative_url }}#lee2026neuralrecording">A 16-Channel Neural Recording IC with Spike-Driven Adaptive-Basis Compressive Sensing</a><span class="rf-venue">Symposium on VLSI Technology and Circuits, 2026</span></li>
          <li><a href="{{ '/publications/' | relative_url }}#lee2022neuralimplant">A Miniaturized Wireless Neural Implant With Body-Coupled Power Delivery and Data Transmission</a><span class="rf-venue">IEEE JSSC, 2022</span></li>
        </ul>
    </div>

  </section>
  <!-- FPGA-based systems: full-width horizontal flow -->
  <section class="rf-section" id="fpga-systems" aria-labelledby="fpga-systems-heading">
    <h2 id="fpga-systems-heading">FPGA-based Systems</h2>
    <p>Custom sensors and readout ICs generate wide, continuous data streams that must be captured with precise timing and processed with predictable latency. We study FPGA architectures for this problem: sensor timing and synchronization, parallel streaming data paths, and the division of processing between programmable logic and host software.</p>
    <ul class="rf-focus">
      <li>Timing, synchronization, and configuration architectures for sensor and ASIC control</li>
      <li>Parallel capture and streaming data paths with configurable signal processing</li>
      <li>Hardware–software partitioning between programmable logic and host-side processing</li>
    </ul>
    <figure class="rf-figure rf-figure--wide">
      <div class="rf-flow" role="img" aria-label="Conceptual FPGA sensor platform: data streams from a sensor or readout IC through programmable logic to host processing, while timing, configuration, and commands flow in the opposite direction.">
        <div class="rf-node rf-node--context"><strong>Sensor or readout IC</strong><span>continuous data source</span></div>
        <div class="rf-link"><span class="rf-lane rf-lane--fwd">data</span><span class="rf-lane rf-lane--rev">control</span></div>
        <div class="rf-node"><strong>FPGA</strong><span>timing · streaming · processing</span></div>
        <div class="rf-link"><span class="rf-lane rf-lane--fwd">data</span><span class="rf-lane rf-lane--rev">commands</span></div>
        <div class="rf-node"><strong>Host processing</strong><span>analysis and control</span></div>
      </div>
      <figcaption>Conceptual FPGA sensor platform. Data streams from the sensor through programmable logic to the host; timing and configuration flow back. The dashed block is the sensor or IC being read out.</figcaption>
    </figure>
  </section>
  <!-- High-speed interfaces: vertical link flow left, text right -->
  <section class="rf-section" id="high-speed-interfaces" aria-labelledby="high-speed-interfaces-heading">
    <h2 id="high-speed-interfaces-heading">High-speed Interfaces</h2>
    <div class="rf-split rf-split--reverse">
      <div class="rf-text">
        <p>Clock jitter, channel loss, and timing skew constrain the bandwidth and energy efficiency of high-speed chip-to-chip links. We study transmitter, receiver, and clocking architectures for serial links, treating the channel's nonidealities as part of the design problem.</p>
        <ul class="rf-focus">
          <li>Transmitters: serializers and differential output drivers</li>
          <li>Clocking: low-jitter clock generation, distribution, and clock and data recovery</li>
          <li>Receivers: equalization (CTLE/DFE), sampling, and timing alignment</li>
        </ul>
      </div>
      <figure class="rf-figure">
        <div class="rf-flow rf-flow--vertical" role="img" aria-label="Conceptual serial link: a transmitter with serializer, driver, and clock generation sends data through an interconnect channel that adds loss, crosstalk, and jitter; a receiver equalizes the signal and aligns timing to sample the data.">
          <div class="rf-node"><strong>Transmitter</strong><span>serializer · driver · clock generation</span></div>
          <div class="rf-link"><span class="rf-lane rf-lane--fwd">serial data</span></div>
          <div class="rf-node rf-node--context"><strong>Interconnect channel</strong><span>loss · reflection · crosstalk</span></div>
          <div class="rf-link"><span class="rf-lane rf-lane--fwd">degraded signal</span></div>
          <div class="rf-node"><strong>Receiver</strong><span>equalization · sampling · alignment</span></div>
        </div>
        <figcaption>Conceptual serial link. Transmitter and receiver circuits must tolerate the loss and timing uncertainty added by the channel (dashed). The clock may be forwarded or recovered, depending on the link.</figcaption>
      </figure>
    </div>
  </section>
  <p class="rf-earlier">Earlier work on bio-impedance sensing, ultrasound receivers, and short-range wireless transceivers remains on the <a href="{{ '/publications/' | relative_url }}">publications</a> page.</p>
</div>
