# LumenIR — Unified IR Blaster & DALI Smart Home Controller

A mobile-first IoT companion application designed for a Wi-Fi-bridged hardware hub featuring both a **built-in 38 kHz Infrared (IR) Blaster** and **DALI / DALI-2 lighting bus control**. It unifies legacy IR appliance remotes (TV, Split AC, Soundbar, Projector), addressable DALI fixtures, IR signal learning, cross-protocol automation scenes, and live protocol telemetry into one tactile controller.

---

## User Review & Critical Decisions

> [!IMPORTANT]
**DALI** (Digital Addressable Lighting Interface), the industry-standard 2-wire architectural lighting bus supporting individual fixture addressing (`A0–A63`), groups (`G0–G15`), DT6 arc dimming, DT8 tunable white/color temperature, and native DALI scenes. 
**Execution Mode (Simulator + Real LAN Bridge):** Out of the box, the app runs a deterministic **Virtual IoT Hub & Room Simulator** (generating real NEC/RC5/Sony/HVAC IR pulse trains and 16-bit Manchester-encoded DALI frames with live appliance state feedback) while also allowing you to configure a **real Wi-Fi Bridge REST endpoint** (e.g., ESP32, Tasmota, ESPHome, or Lunatone DALI-IoT gateway) to dispatch live JSON payloads over your network.

- **Confirmed Hardware Scope**: Single Wi-Fi IoT hub equipped with an integrated 360° 38 kHz IR emitter/receiver and a wired DALI master bus interface.
- **Recommended Default — Appliance Library**: Pre-loaded universal remote profiles for Smart TV (NEC/Samsung), Split AC HVAC (stateful multi-byte frames), Soundbar/AVR (Sony SIRC / RC5), and Ceiling Fan / Projector, plus custom IR Learning capture.
- **Recommended Default — Visual Aesthetic**: Tactile Matte Hardware Dark theme optimized for one-handed mobile thumb ergonomics, expanding cleanly into a multi-column control console on desktop screens.

---

## 1. Overview & Core Concept

- **What It Does**: **LumenIR** acts as the mobile control plane for a dual-protocol Wi-Fi IoT hub. Users control infrared home appliances via ergonomic device-specific remotes, dim and tune wired DALI architectural lights individually or by group, capture raw IR codes from legacy physical remotes via IR Learning Mode, run synchronized cross-protocol scenes (combining DALI lighting fades with delayed IR macros), and inspect every transmitted 38 kHz IR waveform and 16-bit DALI bus frame in real time.
- **Target Audience / Persona**: Smart home integrators, IoT product engineers, and homeowners managing spaces that mix professional wired DALI lighting with consumer infrared appliances (TVs, HVAC units, audio systems).
- **Key Value**: Eliminates remote clutter and protocol silos by letting a single mobile screen—and single-tap macros—orchestrate both one-way infrared bursts and bidirectional DALI lighting states through one Wi-Fi hub.

---

## 2. User Experience & Visual Design

### Key User Flows

1. **Hub Connection & Room Selection (Zero-State to Control)**
   - Users open the **Remotes** workspace directly into an active room hub (e.g., *Living Room Hub — Wi-Fi Bridged*) with immediate one-tap access to paired IR appliances and a top hub strip displaying active room, execution mode (*Virtual Hub* vs. *LAN Bridge*), and quick device pairing.
2. **Universal IR Appliance Control (Thumb-First Ergonomics)**
   - Switching between paired appliances (Smart TV, Split AC, Soundbar, Projector) renders a dedicated tactile hardware keypad sized for $\ge 44 \times 44\text{px}$ touch targets:
     - *Smart TV*: Power, Input, Navigation D-Pad with center OK, Volume/Channel rockers, Mute, and Media controls.
     - *Split AC (Stateful HVAC)*: Large tabular temperature readout (`16°C–30°C`), Mode selector (*Cool, Heat, Dry, Fan, Auto*), Fan Speed, and Louver Swing—each adjustment packs and blasts a complete multi-byte HVAC state frame.
     - *Soundbar / AVR*: Power, Optical/HDMI ARC input selector, Bass/Treble trim, Sound Mode, and Volume dial/rocker.
   - Pressing any key triggers instant tactile press feedback ($\le 150\text{ms}$), fires the IR emitter pulse animation on the virtual hub, updates the live room state, and logs the encoded 38 kHz frame in the protocol inspector.
3. **Add Device Wizard & Universal Protocol Pairing**
   - Users tap **Add Device**, choose an appliance category and brand (e.g., Samsung, LG, Sony, Daikin, Mitsubishi, Bose), and step through an interactive **IR Code-Set Verification** flow—tapping a live *Test Power Signal* button across candidate protocol sets until the appliance responds, then saving the remote to the room.
4. **IR Learning Mode (Raw Pulse Capture)**
   - In the **IR Learn** drawer/modal, users put the hub's IR receiver into listening mode, trigger a simulated or bridge-captured raw 38 kHz signal from an existing physical remote, inspect the decoded protocol/Pronto Hex and microsecond mark/space timings, assign a custom button label and icon, and bind it directly to any remote.
5. **DALI / DALI-2 Architectural Lighting Control**
   - The **DALI Bus** tab provides full control over the hub's 2-wire lighting interface:
     - **Individual Fixtures (`A0–A63`) & Groups (`G0–G15`)**: Arc-power dimming sliders (`0–100%` mapped to DALI 8-bit `0–254` logarithmic levels) and **DT8 Tunable White** Kelvin sliders (`2700K–6500K` mapped to Mirek values) with real-time luminance previews.
     - **Bus Broadcast & Native DALI Scenes**: Instant *All On*, *All Off*, *Fade Rate* controls, and recall/save for native DALI scenes (`Scene 0–15`), plus a live DALI Bus Address Discovery scan.
6. **Unified Cross-Protocol Scenes & Delayed Macros**
   - The **Scenes** tab lets users trigger and build multi-step routines that mix DALI lighting commands and IR bursts with millisecond inter-command delays—for example, *Cinema Mode*:
     - Step 1: `DALI Group 0 (Ceiling)` → Fade to `10%` at `2700K`
     - Step 2: `IR Blaster (NEC)` → Living Room TV `POWER_ON`
     - Step 3: `Delay` → `1500 ms`
     - Step 4: `IR Blaster (NEC)` → Living Room TV `INPUT_HDMI_2`
     - Step 5: `IR Blaster (Sony SIRC)` → Soundbar `POWER_ON`
     - Step 6: `IR Blaster (Daikin HVAC)` → Split AC `22°C · Cool · Quiet`
   - Running a scene shows real-time step-by-step execution progress across both the DALI bus and IR emitter.
7. **Wi-Fi Bridge & Live Protocol Telemetry**
   - The **Bridge & Signals** view (and persistent desktop side inspector on wide screens) displays the live **38 kHz IR Mark/Space Oscilloscope Canvas**, raw hexadecimal/Pronto frames, **DALI 16-bit Forward Frame** binary breakdown (`[Address Byte | Command Byte]` with Manchester encoding visualization), and Wi-Fi Bridge configuration (Hub IP/URL, Auth Token, Toggle between *Virtual Hub Simulator* and *Real HTTP Bridge Webhook*, and JSON payload export).

### Visual Identity & Theme

- **Aesthetic Direction**: Tactile Matte Hardware Control — inspired by precision industrial remotes (Bang & Olufsen, Teenage Engineering, architectural KNX/DALI keypads). Grounded, quiet, high-contrast surfaces with deliberate physical button depth and crisp technical clarity.
- **Color Palette & Mood (60-30-10 Discipline)**:
  - *60% Dominant Neutral Canvas*: Deep matte obsidian (`#0B0D12` / `--background`) to keep focus on active controls and reduce glare in dim living-room / home-theater environments.
  - *30% Structural Surfaces*: Elevated anodized graphite (`#141821` / `--surface`), tactile keycap wells (`#1C212E` / `--surface-raised`), and quiet hairline borders (`#262C3A` / `--border`).
  - *10% Accent Budget*:
    - Infrared Signal Accent: Precision Vermilion/Amber (`#F97316` / `--accent-ir`) reserved strictly for primary actions, active remote states, and live IR transmission pulses.
    - DALI Luminance Accent: Warm Architectural Tungsten (`#FBBF24` / `--accent-dali`) strictly for active DALI dimmer tracks and color-temperature visualizers.
  - *Legibility*: High-contrast off-white primary text (`#F8FAFC`) with subtle optical tracking (`+0.01em`) and cool slate secondary copy (`#94A3B8`). Every status indicator pairs color with explicit text labels (never hue-only).
- **Typography & Hierarchy (2+1 Font Rule)**:
  - *Display & Headings*: **Outfit** (SemiBold 600–700) — clean geometric hardware proportions with `text-wrap: balance`.
  - *UI & Body Copy*: **Plus Jakarta Sans** (Regular 400 / Medium 500) — effortless touch-screen scannability.
  - *Protocol Telemetry & Addresses*: **JetBrains Mono** (`tabular-nums`) — strictly for hex codes, 38 kHz pulse timings, DALI short addresses (`A00–A63`), Kelvin/arc values, and LAN IP addresses.
- **Responsive Mobile-to-Desktop Layout**:
  - *Mobile (`375px–430px`)*: One-handed thumb-zone architecture with a compact top app bar (`52px`) and fixed 4-tab bottom navigation bar (`64px`: **Remotes**, **DALI**, **Scenes**, **Bridge**), strictly keeping aggregate fixed chrome under 15% of viewport height and enforcing $\ge 44 \times 44\text{px}$ hitboxes on all keypad buttons.
  - *Desktop (`1024px–1440px+`)*: Expands into a clean 3-zone Top Bar Contract + spacious 2-column command workspace (`max-w-7xl`): left primary control stage (Active Remote Keypad / DALI Bus Matrix / Scene Composer) paired side-by-side with a live **Virtual Room State & Protocol Oscilloscope** panel so engineers and homeowners see immediate physical + signal-level feedback without scrolling.
- **Anti-Slop Restraint**: Zero pill-badge clutter (metadata rendered as quiet inline text separated by `·`), zero decorative pulsing status dots, zero `//` code-comment headings, and single-elevation surface hierarchy.

### Interactive Feedback & Motion

- **Tactile Key Press**: Immediate `scale(0.96)` spring press and subtle rim highlight settling within `120ms`.
- **Live Transmission Pulse**: When an IR or DALI frame fires, the hub emitter indicator flashes cleanly for the actual burst duration (`~68ms` for NEC, `~14ms` for DALI forward frame) and plots the real-time waveform onto an interactive SVG oscilloscope.
- **State Continuity**: Loading states for DALI bus discovery scans and real LAN webhook dispatches, clean empty states when a room has no custom learned keys, and inline non-blocking toast notifications for bridge responses or connection errors.

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Dual Execution Engine (Interactive Simulator + Optional Real LAN Bridge Proxy)**
  - *Chosen Approach*: Implement a deterministic client-side IR & DALI protocol engine (real NEC, Sony SIRC, RC5, Daikin HVAC, and IEC 62386 DALI frame encoders) paired with an optional Express backend proxy (`/api/bridge/dispatch`) that forwards JSON IR/DALI payloads to a user-configured Wi-Fi hub IP/endpoint.
  - *Why*: Web browsers cannot directly emit 940 nm infrared light or drive a 16V DALI bus, and direct browser requests to local IoT IPs are frequently blocked by CORS. This approach delivers a 100% functional interactive experience immediately while remaining genuinely usable with real ESP32/Tasmota/DALI gateways.
  - *Alternatives Considered*: Purely static mock UI (rejected—fails IoT SME fidelity) or requiring physical hardware before the app works (rejected—blocks interactive testing and design validation).

- **Decision 2: Local Persistence via Structured State Store (`localStorage`)**
  - *Chosen Approach*: Persist paired IR remotes, learned raw IR buttons, DALI fixture/group states, custom scenes, and Wi-Fi bridge settings in `localStorage` with one-click factory reset.
  - *Why*: Instant zero-latency responsiveness without forcing user login walls, ideal for a hardware companion prototype and single-hub local controller.
  - *Alternatives Considered*: Cloud database with mandatory authentication (unnecessary friction since multi-user cloud accounts were not requested).

- **Decision 3: Dedicated Stateful HVAC Remote vs. Generic Grid**
  - *Chosen Approach*: Model Air Conditioners with a stateful protocol packet builder (combining power, mode, setpoint temperature, fan speed, and swing into one transmitted frame) rather than stateless toggle buttons.
  - *Why*: Accurately reflects real-world IR HVAC engineering (Daikin/LG/Midea/Mitsubishi protocols) and demonstrates domain depth.

---

## 4. Technical Architecture & Data Strategy *(Technical Reference)*

### Architecture & Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       LumenIR Mobile & Desktop App                      │
│  ┌──────────────────────┐              ┌─────────────────────────────┐  │
│  │  Mobile Bottom Tabs  │              │  Desktop 3-Zone Top Bar     │  │
│  │  Remotes·DALI·Scenes │              │  Brand — Nav Tabs — +Device │  │
│  └──────────┬───────────┘              └──────────────┬──────────────┘  │
│             └────────────────────┬────────────────────┘                 │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Central Hub State Store                        │  │
│  │  Rooms & Hubs · IR Remotes · Learned Keys · DALI Bus · Scenes     │  │
│  │  Persistence (localStorage) · Active Signal Transmission Bus      │  │
│  └───────────────┬───────────────────────────────────┬───────────────┘  │
│                  ▼                                   ▼                  │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐  │
│  │     Primary Control Stage     │   │  Live Signal & Room Telemetry │  │
│  │  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │  │
│  │  │ Universal IR Remotes    │  │   │  │ Virtual Room Appliances │  │  │
│  │  │ (TV · HVAC · Audio ·    │  │   │  │ (Live TV/AC/Light State)│  │  │
│  │  │  Learned Custom Keys)   │  │   │  └─────────────────────────┘  │  │
│  │  ├─────────────────────────┤  │   │  ┌─────────────────────────┐  │  │
│  │  │ DALI-2 Bus Controller   │  │   │  │ 38kHz IR & DALI Frame   │  │  │
│  │  │ (DT6 Dim · DT8 Kelvin · │  │   │  │ Oscilloscope & Log      │  │  │
│  │  │  Groups · Bus Scan)     │  │   │  └─────────────────────────┘  │  │
│  │  ├─────────────────────────┤  │   └───────────────┬───────────────┘  │
│  │  │ Cross-Protocol Scenes   │  │                   │                  │
│  │  │ (DALI + Delayed IR Seq) │  │                   │                  │
│  │  └─────────────────────────┘  │                   │                  │
│  └───────────────┬───────────────┘                   │                  │
│                  └──────────────────┬────────────────┘                  │
└─────────────────────────────────────┼───────────────────────────────────┘
                                      ▼
            ┌───────────────────────────────────────────────────┐
            │            Protocol Encoder & Dispatcher          │
            │  • IR Encoders (NEC, RC5, Sony SIRC, HVAC Raw)    │
            │  • DALI-2 Frame Builder (16-bit Manchester)       │
            └──────────────┬─────────────────────┬──────────────┘
                           ▼                     ▼
          ┌─────────────────────────┐  ┌───────────────────────────────┐
          │ Virtual Hub Simulator   │  │ Express Proxy (/api/bridge)   │
          │ Updates simulated room  │  │ Forwards JSON payload over    │
          │ appliances & waveforms  │  │ HTTP POST to LAN Wi-Fi Hub    │
          └─────────────────────────┘  └───────────────────────────────┘
```

### Data Model & State

- **Hub (`HubConfig`)**: `id`, `name`, `room`, `mode` (`'simulator' | 'lan-bridge'`), `ipAddress`, `endpointPath`, `apiToken`, `wifiRssiDbm`, `irCarrierKhz` (`38`), `daliBusVoltageV` (`16.0`), `online`.
- **IR Appliance Remote (`IRDevice`)**: `id`, `hubId`, `name`, `category` (`'tv' | 'ac' | 'audio' | 'projector'`), `brand`, `protocol` (`'NEC' | 'SONY_SIRC' | 'RC5' | 'SAMSUNG32' | 'DAIKIN_HVAC'`), `powerState`, `hvacState` (temperature, mode, fan, swing), `mediaState` (volume, muted, input, channel), `customButtons` (learned IR keys with Pronto hex & microsecond timings).
- **DALI Luminaire (`DALIFixture`)**: `shortAddress` (`0–63`), `name`, `zone`, `deviceType` (`'DT6' | 'DT8'`), `groups` (`number[]`), `arcLevel` (`0–254`), `kelvin` (`2700–6500`), `fadeRate`, `isOn`, `lampFailure`.
- **Unified Scene (`AutomationScene`)**: `id`, `name`, `icon`, `steps` (ordered array of `DALI_DIM`, `DALI_SCENE`, `IR_COMMAND`, `IR_HVAC_STATE`, or `DELAY_MS`).
- **Signal Telemetry Entry (`SignalLogEntry`)**: `id`, `timestamp`, `bus` (`'IR' | 'DALI'`), `protocol`, `targetName`, `commandLabel`, `hexFrame`, `timingMicros` (for IR oscilloscope) or `binaryBits` (for DALI 16-bit Manchester visualization), `deliveryStatus`.

### Interactive Component & State Mapping

- **IR Remote Keypads (`TV`, `HVAC`, `Audio`, `Custom`)**: Pressing any button builds the exact protocol packet (e.g., 32-bit NEC address/command + inverted checksum, or 64-bit stateful HVAC payload), triggers the dispatcher, updates simulated device state immediately, renders the 38 kHz mark/space burst on the oscilloscope, and appends to the signal log.
- **Add Device Pairing Sheet**: Multi-step modal (Category → Brand → Live Protocol Code-Set Test → Confirm & Save) that appends a fully functional new `IRDevice` to the active room and selects it.
- **IR Signal Learning Modal**: Enters listening state, captures a physical/simulated raw burst (displaying carrier frequency, pulse count, and Pronto hex), validates button name input, and appends a working custom button directly onto the selected remote.
- **DALI Bus Controller**: Adjusting any fixture or group slider computes DALI logarithmic arc power (`0–254`) or DT8 Mirek color temperature (`154–370`), dispatches the 16-bit DALI forward frame (`[YAAA AAA0][Arc/Cmd]`), and updates room lighting levels immediately. Clicking **Scan DALI Bus** runs an animated sequential address discovery sweep (`A00–A63`) that reports connected drivers and bus health.
- **Scene Runner & Composer**: Clicking **Run Scene** executes each step sequentially with real `setTimeout` delays, highlighting the active step and updating both DALI fixtures and IR appliances live; users can also create or delete custom scenes via the Scene Builder sheet.
- **Wi-Fi Bridge Settings & LAN Dispatch**: Toggling to *Real LAN Bridge* enables live HTTP POST dispatch through the Express proxy route `/api/bridge/dispatch` with input validation (preventing invalid URLs), timeout handling, and clear inline success/error feedback while gracefully preserving local UI responsiveness.

### Key Sequences & Integrations

1. **IR Command Dispatch Sequence**:
   `Button Press` → `IR Protocol Encoder (NEC/RC5/SIRC/HVAC)` → `Generate Mark/Space µs Array + Hex` → `Update Virtual Appliance + Plot 38kHz Waveform` → *(If LAN Bridge active)* `POST /api/bridge/dispatch` → `Target ESP32/Tasmota Wi-Fi Hub` → `Render ACK / Error Toast`.
2. **DALI-2 Bus Command Sequence**:
   `Dimmer/Kelvin Change` → `Convert % to 8-bit Arc (0–254) or Kelvin to Mirek` → `Build 16-bit Forward Frame (Address + Command)` → `Encode Manchester Bitstream` → `Update Luminaire State + Plot DALI Frame` → *(If LAN Bridge active)* `POST /api/bridge/dispatch`.
