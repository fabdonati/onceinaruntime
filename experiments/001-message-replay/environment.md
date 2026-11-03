# Initial execution environment

Inspected 1 November 2026. This is the locally available execution host; it has not been established as the intended machine for a full measurement campaign.

| Item | Observed |
| --- | --- |
| OS | macOS 15.6.1 (24G90), Darwin 24.6.0, ARM64 |
| Execution | `kern.hv_vmm_present=0`; no hypervisor reported by this query |
| CPU | Apple M3, Mac15,12; 8 physical and logical cores, no SMT |
| Topology | 4 performance and 4 efficiency cores; no thread pinning used |
| Cache | 128-byte lines; performance cluster L2 16 MiB, efficiency cluster L2 4 MiB; generic L1I/L1D values 128/64 KiB, not a complete per-cluster inventory |
| Other caches | L3 query returned no value; system-level cache not established |
| RAM | 16 GiB |
| C++ | Apple Clang 17.0.0 (clang-1700.0.13.5); libc++ macro 190102; C++20 probe succeeded |
| Build | CMake 4.3.1; Unix Makefiles; Ninja absent |
| Python | Homebrew Python 3.14.4; isolated `.venv` for Matplotlib |
| Profiling | `sample` exists. Full Xcode's `xctrace` is unavailable with the active Command Line Tools directory. Linux perf absent. Hardware counter access not established. |
| Power | Battery power at initial inventory, low power mode disabled; actual settings and charge are in raw inventory |

Hardware inventory queries can fail when permissions are restricted. The recorder preserves those failures instead of filling in guessed values. Capture a fresh inventory with every measurement campaign.

No power settings, affinity, scheduler, OS or toolchain installations were changed. Background load, clock frequencies, thermal state and P/E-core placement are uncontrolled. Use these observations for functional validation and preliminary harness checks. Before full measurements, use stable power, choose the intended host, assess variation and timing scale, and record the conditions again. No Linux scheduling or cache-causation claims follow from this setup.
