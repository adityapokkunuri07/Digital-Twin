"""
Session Status Enum — Explicit, Unambiguous Session States (§6A).

Replaces generic string literals like "GATHERING", "PENDING_REVIEW", "IN_PROGRESS"
with explicit states that make the wait-reason visible from the status alone.

Bhanu sir's rule: "Replace generic 'On Hold' with explicit, unambiguous states:
awaiting_user_input, awaiting_expert_intervention, etc."
"""
from enum import Enum


class SessionStatus(str, Enum):
    """
    Every session state explicitly identifies what the system is waiting for.
    No ambiguous states permitted.
    """
    # Active — system is waiting for end-user input
    AWAITING_USER_INPUT = "awaiting_user_input"

    # Processing — system is computing (not waiting for anyone)
    PROCESSING = "processing"
    PROCESSING_SYNTHESIS = "processing_synthesis"
    PROCESSING_PARTIAL_SYNTHESIS = "processing_partial_synthesis"

    # Blocked — waiting for the human expert
    AWAITING_EXPERT_INTERVENTION = "awaiting_expert_intervention"

    # Post-review — expert approved, awaiting downstream action
    AWAITING_BOOKING = "awaiting_booking"

    # In-flight external call
    PROCESSING_BOOKING = "processing_booking"

    # Terminal states
    COMPLETE_BOOKED = "complete_booked"
    COMPLETE_CLOSED = "complete_closed"

    # Failure states
    FAILED_BOOKING = "failed_booking"
