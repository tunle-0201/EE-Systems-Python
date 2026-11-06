"""
spacewire_edge_link_state_machine.py - SpaceWire Link State Machine & Credit Flow Control

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: SpaceX Starship Flight Computer / Satellite Instrument Payload Bus
Standard: ECSS-E-ST-50-52C SpaceWire Protocol Link Layer State Machine & Flow Control

MATHEMATICAL FOUNDATION & LINK LAYER SPECIFICATION:
1. 6-State Finite State Machine (ECSS-E-ST-50-52C Section 8.5):
   - ErrorReset : Transmitters disabled, receiver buffers flushed.
   - ErrorWait  : Enforces 6.4 us of silence (Exchange of Silence) to ensure partner resets.
   - Ready      : Waiting for LinkStart or AutoStart enable signal.
   - Started    : Transmits NULL characters; waiting for incoming NULL from partner.
   - Connecting : Transmits FCT (Flow Control Token) + NULLs; waiting for partner FCT.
   - Run        : Full operational state! Data characters (N-Chars), EOP, and EEP permitted.

2. Exchange of Silence (6.4 us):
   Guarantees both sides of the flight harness detect link disconnection before
   attempting re-synchronization, avoiding stale partial tokens.

3. Credit-Based Flow Control (FCT - Flow Control Tokens):
   - Receiver has limited FIFO buffer depth (e.g. 56 or 64 characters).
   - Each FCT token transmitted grants the partner exactly 8 Data Character credits:

      Tx_Credit = Tx_Credit + 8   (upon receiving an FCT token)
      Tx_Credit = Tx_Credit - 1   (upon transmitting one Data character)

   If Tx_Credit == 0, transmitter stops sending data immediately (zero buffer overflow).
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import deque


class LinkState(Enum):
    ERROR_RESET = "ERROR_RESET"
    ERROR_WAIT  = "ERROR_WAIT"
    READY       = "READY"
    STARTED     = "STARTED"
    CONNECTING  = "CONNECTING"
    RUN         = "RUN"


class SpwCharType(Enum):
    NULL_CHAR = "NULL"   # Synchronization heartbeat
    FCT_CHAR  = "FCT"    # Flow Control Token (+8 credits)
    DATA_CHAR = "DATA"   # 8-bit Data payload character (N-Char)
    EOP_CHAR  = "EOP"    # End of Packet marker
    EEP_CHAR  = "EEP"    # Error End of Packet (abort marker)


class SpwControlToken:
    """Represents a SpaceWire link-layer token."""
    def __init__(self, char_type: SpwCharType, value: int = 0):
        self.char_type = char_type
        self.value = value & 0xFF


class SpaceWireLinkStateMachine:
    """
    ECSS-E-ST-50-52C Compliant SpaceWire Link State Machine (LSM).
    """
    SILENCE_CYCLES = 64  # Scaled discrete cycles representing 6.4 us Exchange of Silence

    def __init__(self, node_id: str, rx_buffer_depth: int = 56):
        self.node_id = node_id
        self.rx_buffer_depth = rx_buffer_depth
        self.state = LinkState.ERROR_RESET

        # Control flags
        self.link_start = True
        self.auto_start = False

        # State timers
        self.silence_timer = 0

        # Flow control credits
        self.tx_credit = 0
        self.pending_fct_count = 0
        self.rx_fifo: deque[int] = deque()

        # Telemetry
        self.state_history: List[LinkState] = [self.state]
        self.data_chars_sent = 0
        self.data_chars_received = 0

    def step(self, rx_token: Optional[SpwControlToken]) -> Optional[SpwControlToken]:
        """
        Executes one clock cycle of the SpaceWire Link State Machine.
        Accepts incoming token from remote partner; returns token to transmit.
        """
        tx_token = None

        # 1. State Machine Transitions
        if self.state == LinkState.ERROR_RESET:
            self.tx_credit = 0
            self.pending_fct_count = 0
            self.silence_timer = 0
            self.state = LinkState.ERROR_WAIT

        elif self.state == LinkState.ERROR_WAIT:
            self.silence_timer += 1
            if self.silence_timer >= self.SILENCE_CYCLES:
                self.state = LinkState.READY

        elif self.state == LinkState.READY:
            if self.link_start or (self.auto_start and rx_token is not None):
                self.state = LinkState.STARTED
                tx_token = SpwControlToken(SpwCharType.NULL_CHAR)

        elif self.state == LinkState.STARTED:
            tx_token = SpwControlToken(SpwCharType.NULL_CHAR)
            if rx_token is not None and rx_token.char_type == SpwCharType.NULL_CHAR:
                self.state = LinkState.CONNECTING

        elif self.state == LinkState.CONNECTING:
            # Send initial FCT token to grant credits to partner
            tx_token = SpwControlToken(SpwCharType.FCT_CHAR)
            if rx_token is not None and rx_token.char_type == SpwCharType.FCT_CHAR:
                self.tx_credit += 8
                self.state = LinkState.RUN

        elif self.state == LinkState.RUN:
            # Process received token
            if rx_token is not None:
                if rx_token.char_type == SpwCharType.FCT_CHAR:
                    self.tx_credit += 8
                elif rx_token.char_type == SpwCharType.DATA_CHAR:
                    self.rx_fifo.append(rx_token.value)
                    self.data_chars_received += 1

            # Emit scheduled FCT token if any, else maintain link with NULL
            if self.pending_fct_count > 0:
                self.pending_fct_count -= 1
                tx_token = SpwControlToken(SpwCharType.FCT_CHAR)
            else:
                tx_token = SpwControlToken(SpwCharType.NULL_CHAR)

        if self.state != self.state_history[-1]:
            self.state_history.append(self.state)

        return tx_token

    def read_received_buffer(self) -> List[int]:
        """Flight software reads and empties received FIFO, scheduling credit replenishment."""
        data = list(self.rx_fifo)
        self.rx_fifo.clear()
        # Schedule FCT token to replenish 8 credits
        self.pending_fct_count += 1
        return data

    def send_data_byte(self, byte_val: int) -> Optional[SpwControlToken]:
        """Attempts to transmit a data character if credits are available."""
        if self.state != LinkState.RUN:
            return None
        if self.tx_credit <= 0:
            return None  # Paused by flow control credit exhaustion!

        self.tx_credit -= 1
        self.data_chars_sent += 1
        return SpwControlToken(SpwCharType.DATA_CHAR, value=byte_val)

    def trigger_disconnect_error(self) -> None:
        """Forces link into ErrorReset upon cable disconnect or parity fault."""
        self.state = LinkState.ERROR_RESET
        self.state_history.append(self.state)


def test_spacewire_link_state_machine():
    print("================================================================================")
    print("TEST SUITE: SPACEWIRE LINK STATE MACHINE (LSM) & CREDIT FLOW CONTROL")
    print("================================================================================")

    # Instantiate flight computer node and satellite payload instrument node
    node_a = SpaceWireLinkStateMachine("Starship_Flight_Comp", rx_buffer_depth=56)
    node_b = SpaceWireLinkStateMachine("Starship_IMU_Nav_Payload", rx_buffer_depth=56)

    # 1. Step through Exchange of Silence & Connection Handshake
    token_a_to_b = None
    token_b_to_a = None

    connection_cycle = 0
    while not (node_a.state == LinkState.RUN and node_b.state == LinkState.RUN):
        token_out_a = node_a.step(token_b_to_a)
        token_out_b = node_b.step(token_a_to_b)
        token_a_to_b = token_out_a
        token_b_to_a = token_out_b
        connection_cycle += 1
        assert connection_cycle < 200, "Connection timed out"

    print(f"Link Connection Established in {connection_cycle} cycles!")
    print(f"Node A State Sequence: {[s.value for s in node_a.state_history]}")
    print(f"Node B State Sequence: {[s.value for s in node_b.state_history]}")

    assert node_a.state == LinkState.RUN and node_b.state == LinkState.RUN
    # Both nodes must have passed through ErrorReset -> ErrorWait -> Ready -> Started -> Connecting -> Run
    expected_fsm = [
        LinkState.ERROR_RESET, LinkState.ERROR_WAIT, LinkState.READY,
        LinkState.STARTED, LinkState.CONNECTING, LinkState.RUN
    ]
    assert node_a.state_history == expected_fsm
    assert node_b.state_history == expected_fsm
    print("[PASS] Milestone 1: SpaceWire 6-State FSM & Exchange of Silence handshake verified.")

    # 2. Credit-Based Flow Control Verification
    # Initial credit allocated by connecting FCT
    print(f"\nInitial Tx Credits: Node A={node_a.tx_credit}, Node B={node_b.tx_credit}")
    assert node_a.tx_credit == 8

    # Node A transmits a telemetry burst of 8 bytes (depleting credits to 0)
    burst_bytes = [0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80]
    for b in burst_bytes:
        tok = node_a.send_data_byte(b)
        assert tok is not None
        node_b.step(tok)

    assert node_a.tx_credit == 0
    print(f"After 8-Byte Burst: Node A Tx Credits = {node_a.tx_credit}")

    # Attempting 9th byte must be blocked by flow control!
    blocked_tok = node_a.send_data_byte(0x99)
    assert blocked_tok is None, "Transmitter must pause when credits reach zero"
    print("[PASS] Milestone 2: Credit exhaustion prevents buffer overflow at receiver.")

    # 3. Simulate Receiver Processing & FCT Replenishment
    # Flight software at Node B reads the 8-byte packet, scheduling FCT token
    received_packet = node_b.read_received_buffer()
    assert received_packet == burst_bytes
    print(f"Node B Consumed Packet: {[hex(x) for x in received_packet]}")

    # Node B steps and transmits scheduled FCT to Node A
    fct_reply = node_b.step(None)
    assert fct_reply is not None and fct_reply.char_type == SpwCharType.FCT_CHAR
    node_a.step(fct_reply)

    assert node_a.tx_credit == 8
    print(f"After FCT Replenishment: Node A Tx Credits restored to {node_a.tx_credit}")

    # Now 9th byte can be transmitted cleanly
    unblocked_tok = node_a.send_data_byte(0x99)
    assert unblocked_tok is not None
    print("[PASS] Milestone 3: Flow Control Token (FCT) replenishes credits dynamically.")

    # 4. Cable Disconnect Error Recovery
    node_a.trigger_disconnect_error()
    assert node_a.state == LinkState.ERROR_RESET
    print("[PASS] Milestone 4: Hardware disconnect immediately forces ErrorReset state.")
    print("================================================================================")
    print("ALL MILESTONE BB.2 SPACEWIRE LSM & FLOW CONTROL TESTS PASSED!")
    print("================================================================================")


if __name__ == "__main__":
    test_spacewire_link_state_machine()
