"""
noc_edge_mesi_coherence_controller.py - Multi-Core Hardware MESI Cache Coherence Controller

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Silicon Multi-Core CPU/GPU Clusters & Tesla Dojo D1 Processing Nodes
Application: Hardware Cache Coherence, Snooping Bus, & Directory Interconnect

MATHEMATICAL FOUNDATION & MESI PROTOCOL SPECIFICATION:
1. Four Discrete Coherence States:
   - MODIFIED (M) : Line is present ONLY in this cache, and is DIRTY (differs from memory).
   - EXCLUSIVE (E): Line is present ONLY in this cache, and is CLEAN (matches memory).
   - SHARED (S)   : Line may be cached in multiple cores, and is CLEAN.
   - INVALID (I)  : Line is invalid/stale. Any access triggers a cache miss.

2. State Transition Invariants (Coherence Safety):
   - Single-Writer Multiple-Reader (SWMR) Invariant:
     For any memory address A at any physical clock cycle t:
     * Either exactly ONE cache is in MODIFIED (M) state, and all other caches are in INVALID (I).
     * OR zero caches are in MODIFIED, and N caches (N >= 0) are in SHARED (S) or EXCLUSIVE (E).

3. Local Processor Requests:
   - PrRd: Local processor requests a 64-byte cache line Read.
   - PrWr: Local processor requests a 64-byte cache line Write.

4. Bus Snooping Transactions:
   - BusRd  : Read request broadcasted across interconnect (no intent to modify).
   - BusRdX : Read request with intent to modify (invalidates all other caches).
   - BusUpgr: Upgrade request (invalidate others when promoting S -> M).
   - Flush  : Writeback of dirty line to Main Memory / L3 System-Level Cache.
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional


class MesiState(Enum):
    MODIFIED  = "M"  # Exclusive, Dirty
    EXCLUSIVE = "E"  # Exclusive, Clean
    SHARED    = "S"  # Shared, Clean
    INVALID   = "I"  # Invalid


class BusMessageType(Enum):
    BUS_RD   = "BUS_RD"    # Read miss
    BUS_RDX  = "BUS_RDX"   # Write miss (Read with intent to modify)
    BUS_UPGR = "BUS_UPGR"  # Write hit on Shared line (Upgrade)
    FLUSH    = "FLUSH"     # Dirty data written back to memory


class CacheLine:
    """Represents a 64-byte cache line inside a private L1/L2 cache."""
    def __init__(self, tag: int, data: int = 0, state: MesiState = MesiState.INVALID):
        self.tag = tag
        self.data = data
        self.state = state


class SnoopingCoherenceBus:
    """
    Simulates high-speed Coherent Snooping Interconnect connecting all core caches
    and the unified L3 System Level Cache (SLC) / Main Memory.
    """
    def __init__(self):
        self.controllers: List['CoreCacheController'] = []
        self.main_memory: Dict[int, int] = {}  # Address -> 64-byte data word
        self.bus_transactions_total = 0

    def register_controller(self, controller: 'CoreCacheController') -> None:
        self.controllers.append(controller)

    def memory_read(self, address: int) -> int:
        return self.main_memory.get(address, 0x0000)

    def memory_write(self, address: int, data: int) -> None:
        self.main_memory[address] = data

    def broadcast_transaction(
        self,
        initiator: 'CoreCacheController',
        msg_type: BusMessageType,
        address: int,
        data: Optional[int] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Broadcasts transaction on snooping bus.
        Returns:
          - others_have_copy: True if at least one other cache holds this address.
          - supplied_data: Data provided by a peer cache (if modified), else None.
        """
        self.bus_transactions_total += 1
        others_have_copy = False
        supplied_data = None

        for controller in self.controllers:
            if controller == initiator:
                continue

            has_copy, dirty_data = controller.snoop(msg_type, address)
            if has_copy:
                others_have_copy = True
            if dirty_data is not None:
                supplied_data = dirty_data
                # Update main memory with flushed dirty data
                self.memory_write(address, dirty_data)

        return others_have_copy, supplied_data


class CoreCacheController:
    """
    Private L1/L2 Cache Controller executing the MESI hardware state machine.
    """
    def __init__(self, core_id: int, bus: SnoopingCoherenceBus, num_lines: int = 16):
        self.core_id = core_id
        self.bus = bus
        self.num_lines = num_lines
        self.lines: Dict[int, CacheLine] = {}  # Address -> CacheLine
        self.bus.register_controller(self)

        # Telemetry
        self.read_hits = 0
        self.read_misses = 0
        self.write_hits = 0
        self.write_misses = 0

    def read(self, address: int) -> int:
        """Processor Read request (PrRd)."""
        line = self.lines.get(address)
        if line is not None and line.state != MesiState.INVALID:
            self.read_hits += 1
            return line.data

        # Read Miss -> Issue BusRd
        self.read_misses += 1
        others_have, peer_data = self.bus.broadcast_transaction(self, BusMessageType.BUS_RD, address)

        # Obtain data from peer or memory
        data = peer_data if peer_data is not None else self.bus.memory_read(address)

        # Transition state: Exclusive if no one else has it, Shared if others have it
        new_state = MesiState.SHARED if others_have else MesiState.EXCLUSIVE
        self.lines[address] = CacheLine(tag=address, data=data, state=new_state)
        return data

    def write(self, address: int, new_data: int) -> None:
        """Processor Write request (PrWr)."""
        line = self.lines.get(address)

        if line is not None and line.state != MesiState.INVALID:
            # Hit in cache
            self.write_hits += 1
            if line.state == MesiState.MODIFIED:
                # Silent write hit, no bus broadcast needed
                line.data = new_data
            elif line.state == MesiState.EXCLUSIVE:
                # Silent promotion to Modified, no bus broadcast needed!
                line.state = MesiState.MODIFIED
                line.data = new_data
            elif line.state == MesiState.SHARED:
                # Must invalidate other caches before modifying
                self.bus.broadcast_transaction(self, BusMessageType.BUS_UPGR, address)
                line.state = MesiState.MODIFIED
                line.data = new_data
        else:
            # Write Miss -> Issue BusRdX (Read with intent to modify)
            self.write_misses += 1
            _, peer_data = self.bus.broadcast_transaction(self, BusMessageType.BUS_RDX, address)
            self.lines[address] = CacheLine(tag=address, data=new_data, state=MesiState.MODIFIED)

    def snoop(self, msg_type: BusMessageType, address: int) -> Tuple[bool, Optional[int]]:
        """
        Snoop interface: responds to transactions initiated by peer cores on the bus.
        """
        line = self.lines.get(address)
        if line is None or line.state == MesiState.INVALID:
            return False, None

        has_copy = True
        dirty_flush = None

        if msg_type == BusMessageType.BUS_RD:
            # Peer wants to read
            if line.state == MesiState.MODIFIED:
                # Supply dirty data, flush to memory, demote to Shared
                dirty_flush = line.data
                line.state = MesiState.SHARED
            elif line.state == MesiState.EXCLUSIVE:
                # Demote to Shared
                line.state = MesiState.SHARED
            elif line.state == MesiState.SHARED:
                pass  # Remain Shared

        elif msg_type in (BusMessageType.BUS_RDX, BusMessageType.BUS_UPGR):
            # Peer wants exclusive ownership to write -> Invalidate local copy!
            if line.state == MesiState.MODIFIED:
                dirty_flush = line.data  # Writeback dirty data
            line.state = MesiState.INVALID

        return has_copy, dirty_flush


def test_mesi_cache_coherence():
    print("================================================================================")
    print("TEST SUITE: MULTI-CORE HARDWARE MESI CACHE COHERENCE CONTROLLER")
    print("================================================================================")

    bus = SnoopingCoherenceBus()
    # Instantiate 4-Core CPU/Neural Cluster (Apple Silicon M-Series architecture)
    core0 = CoreCacheController(core_id=0, bus=bus)
    core1 = CoreCacheController(core_id=1, bus=bus)
    core2 = CoreCacheController(core_id=2, bus=bus)
    core3 = CoreCacheController(core_id=3, bus=bus)

    addr_A = 0x1000
    addr_B = 0x2000

    # 1. Core 0 reads addr_A -> Cold miss, no one else has it -> Transitions to EXCLUSIVE
    val = core0.read(addr_A)
    assert core0.lines[addr_A].state == MesiState.EXCLUSIVE
    print(f"[PASS] Step 1: Core 0 reads 0x{addr_A:X} -> State: EXCLUSIVE (Clean, Exclusive)")

    # 2. Core 1 reads addr_A -> BusRd snooped by Core 0 -> Core 0 demotes to SHARED, Core 1 enters SHARED
    val = core1.read(addr_A)
    assert core0.lines[addr_A].state == MesiState.SHARED
    assert core1.lines[addr_A].state == MesiState.SHARED
    print(f"[PASS] Step 2: Core 1 reads 0x{addr_A:X} -> Cores 0 & 1 transition to SHARED")

    # 3. Core 1 writes addr_A -> Write hit on SHARED line -> Issues BusUpgr -> Core 0 INVALIDATED, Core 1 MODIFIED
    core1.write(addr_A, 0xDEADBEEF)
    assert core1.lines[addr_A].state == MesiState.MODIFIED
    assert core0.lines[addr_A].state == MesiState.INVALID
    print(f"[PASS] Step 3: Core 1 writes 0x{addr_A:X} -> Core 1: MODIFIED, Core 0: INVALIDATED")

    # 4. Core 2 reads addr_A -> Read miss -> BusRd snooped by Core 1 (MODIFIED) -> Core 1 flushes data to memory and demotes to SHARED, Core 2 enters SHARED with fresh data
    read_val_core2 = core2.read(addr_A)
    assert read_val_core2 == 0xDEADBEEF
    assert core1.lines[addr_A].state == MesiState.SHARED
    assert core2.lines[addr_A].state == MesiState.SHARED
    print(f"[PASS] Step 4: Core 2 reads 0x{addr_A:X} -> Received fresh data 0x{read_val_core2:X}, both in SHARED")

    # 5. Core 3 write miss to addr_B -> BusRdX -> Enters MODIFIED
    core3.write(addr_B, 0xCAFEBABE)
    assert core3.lines[addr_B].state == MesiState.MODIFIED
    print(f"[PASS] Step 5: Core 3 write miss to 0x{addr_B:X} -> Enters MODIFIED")

    # 6. Verify Single-Writer Multiple-Reader (SWMR) Invariant across all addresses
    for addr in [addr_A, addr_B]:
        modified_count = 0
        shared_count = 0
        for c in [core0, core1, core2, core3]:
            l = c.lines.get(addr)
            if l is not None:
                if l.state == MesiState.MODIFIED:
                    modified_count += 1
                elif l.state in (MesiState.SHARED, MesiState.EXCLUSIVE):
                    shared_count += 1
        if modified_count > 0:
            assert modified_count == 1 and shared_count == 0, f"SWMR Invariant violated at address 0x{addr:X}!"

    print(f"Total Bus Coherence Transactions: {bus.bus_transactions_total}")
    print("[PASS] Milestone AY.2: MESI Coherence Controller verified with 100% SWMR invariant compliance!")
    print("================================================================================")


if __name__ == "__main__":
    test_mesi_cache_coherence()
