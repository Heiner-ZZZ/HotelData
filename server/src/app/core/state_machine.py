"""Centralized State Machine for HotelData domain entities.

Provides a single source of truth for state definitions, valid transitions,
labels, and colors across all modules (reservations, housekeeping/rooms,
billing/invoices, payments, maintenance/housekeeping tasks, check-in/out).

Usage:
    from src.app.core.state_machine import booking_sm

    if booking_sm.can_transition(current, target):
        booking_sm.validate_transition(current, target)  # raises ValueError
        next_states = booking_sm.get_valid_next_states(current)
        label = booking_sm.get_state_label(target)
"""

from __future__ import annotations

from typing import Any


# =============================================================================
#  Generic State Machine
# =============================================================================

class StateMachine:
    """Immutable state machine that defines valid transitions for an entity type.

    All transition rules are defined at construction time and stored in a
    lookup dict for O(1) validation — no loops, no branching at runtime.

    Attributes
    ----------
    name : str
        Human-readable entity name (e.g. "booking", "room", "invoice").
    states : dict[str, str]
        Machine-readable key → display label.
    _transitions : dict[str, list[str]]
        Current state → list of valid next states.
    _reverse : dict[str, list[str]]
        Next state → list of valid current states (built from _transitions).
    colors : dict[str, str]
        State key → hex colour string (optional).
    """

    def __init__(
        self,
        name: str,
        states: dict[str, str],
        transitions: dict[str, list[str]],
        colors: dict[str, str] | None = None,
    ) -> None:
        if not name:
            raise ValueError("StateMachine name is required")
        if not states:
            raise ValueError(f"StateMachine '{name}' requires at least one state")
        if not transitions:
            raise ValueError(f"StateMachine '{name}' requires at least one transition rule")

        # Validate all keys in transitions and reverse exist in states
        all_states = set(states)
        for current, next_list in transitions.items():
            if current not in all_states:
                raise ValueError(
                    f"{name}: transition key '{current}' is not a known state. "
                    f"Known: {sorted(all_states)}"
                )
            for nxt in next_list:
                if nxt not in all_states:
                    raise ValueError(
                        f"{name}: transition target '{nxt}' (from '{current}') "
                        f"is not a known state. Known: {sorted(all_states)}"
                    )

        self.name = name
        self.states = dict(states)  # defensive copy
        self._transitions = {k: list(v) for k, v in transitions.items()}
        self.colors = dict(colors) if colors else {}

        # Build reverse lookup: target → [valid current states]
        reverse: dict[str, list[str]] = {s: [] for s in all_states}
        for current, next_list in transitions.items():
            for nxt in next_list:
                reverse.setdefault(nxt, []).append(current)
        self._reverse = {k: sorted(set(v)) for k, v in reverse.items()}

    # ── Public API ──────────────────────────────────────────────────────────

    def can_transition(self, current: str, target: str) -> bool:
        """Return True if the transition from ``current`` to ``target`` is valid."""
        allowed = self._transitions.get(current)
        if allowed is None:
            return False
        return target in allowed

    def validate_transition(self, current: str, target: str) -> None:
        """Raise ``ValueError`` if the transition from ``current`` to ``target``
        is not allowed, with a descriptive message listing valid options."""
        if current not in self.states:
            raise ValueError(
                f"[{self.name}] Estado actual desconocido: '{current}'. "
                f"Valores válidos: {sorted(self.states)}"
            )
        if target not in self.states:
            raise ValueError(
                f"[{self.name}] Estado destino desconocido: '{target}'. "
                f"Valores válidos: {sorted(self.states)}"
            )
        allowed = self._transitions.get(current, [])
        if not allowed:
            raise ValueError(
                f"[{self.name}] El estado '{current}' ({self.states[current]}) "
                f"es terminal — no se permiten más transiciones desde aquí."
            )
        if target not in allowed:
            valid_options = ', '.join(f"'{s}'" for s in allowed)
            raise ValueError(
                f"[{self.name}] Transición inválida: "
                f"'{current}' ({self.states[current]}) → "
                f"'{target}' ({self.states[target]}). "
                f"Transiciones válidas desde '{current}': "
                f"{valid_options}"
            )

    def get_valid_next_states(self, current: str) -> list[str]:
        """Return list of valid target states from ``current`` (empty = terminal)."""
        return list(self._transitions.get(current, []))

    def get_valid_previous_states(self, target: str) -> list[str]:
        """Return list of states that can transition to ``target``."""
        return list(self._reverse.get(target, []))

    def get_state_label(self, state: str) -> str:
        """Return the human-readable label for a state key."""
        return self.states.get(state, state)

    def get_state_color(self, state: str) -> str | None:
        """Return the hex colour for a state, or ``None``."""
        return self.colors.get(state)

    def is_terminal(self, state: str) -> bool:
        """Return True if the state has no outgoing transitions."""
        return not bool(self._transitions.get(state))

    def is_initial(self, state: str) -> bool:
        """Return True if no other state can transition into this state.

        Note: the state at index 0 of the transitions dict is typically the
        initial state, but this method is a stronger check — a state is
        "initial" if nothing can transition *into* it.
        """
        prev = self._reverse.get(state, [])
        return len(prev) == 0

    def get_all_states(self) -> dict[str, str]:
        """Return a copy of all states with their labels."""
        return dict(self.states)

    def get_all_transitions(self) -> dict[str, list[str]]:
        """Return a copy of all valid transitions."""
        return {k: list(v) for k, v in self._transitions.items()}

    def get_all_colors(self) -> dict[str, str]:
        """Return a copy of all state colors."""
        return dict(self.colors)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the full machine definition for API responses (e.g. for
        a frontend dropdown builder)."""
        return {
            "name": self.name,
            "states": dict(self.states),
            "transitions": {k: list(v) for k, v in self._transitions.items()},
            "reverse": dict(self._reverse),
            "colors": dict(self.colors),
            "terminal_states": [s for s in self.states if self.is_terminal(s)],
            "initial_states": [s for s in self.states if self.is_initial(s)],
        }


# =============================================================================
#  Booking (reservation) status machine
# =============================================================================
# Lifecycle: pending → confirmed → checked_in → checked_out
#                     → rejected (terminal)
#           Any active state → cancelled (terminal)

BOOKING_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "confirmed": "Confirmada",
    "rejected": "Rechazada",
    "checked_in": "Check-in Realizado",
    "checked_out": "Check-out Realizado",
    "cancelled": "Cancelada",
}

BOOKING_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["confirmed", "rejected", "cancelled"],
    "confirmed": ["checked_in", "cancelled"],
    "rejected": [],               # terminal
    "checked_in": ["checked_out"],
    "checked_out": [],            # terminal
    "cancelled": [],              # terminal
}

BOOKING_COLORS: dict[str, str] = {
    "pending": "#ca8a04",        # amber
    "confirmed": "#006076",       # primary
    "rejected": "#ba1a1a",       # error
    "checked_in": "#16a34a",     # green
    "checked_out": "#4338ca",    # indigo
    "cancelled": "#6f797d",      # outline
}

booking_sm = StateMachine(
    name="booking",
    states=BOOKING_STATES,
    transitions=BOOKING_TRANSITIONS,
    colors=BOOKING_COLORS,
)

# Stay-status sub-machine (orthogonal to booking.status)
#   pending (not checked in) → checked_in → checked_out → (done)

STAY_STATES: dict[str, str] = {
    "pending": "Sin Registrar",
    "checked_in": "Check-in Realizado",
    "checked_out": "Check-out Realizado",
    "no_show": "No Show",
}

STAY_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["checked_in", "no_show"],
    "checked_in": ["checked_out"],
    "checked_out": [],
    "no_show": [],
}

STAY_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "checked_in": "#16a34a",
    "checked_out": "#4338ca",
    "no_show": "#ba1a1a",
}

stay_sm = StateMachine(
    name="stay",
    states=STAY_STATES,
    transitions=STAY_TRANSITIONS,
    colors=STAY_COLORS,
)


# =============================================================================
#  Room (housekeeping) status machine
# =============================================================================
# The complete housekeeping cycle:
#   vacant_dirty → cleaning_in_progress → cleaning_completed → inspected → vacant_clean
#   occupied_clean → occupied_dirty → cleaning_in_progress
#   Any → maintenance_requested → out_of_service / out_of_order → inspected

ROOM_STATES: dict[str, str] = {
    "vacant_dirty": "Vacante Sucia",
    "vacant_clean": "Vacante Limpia",
    "occupied_clean": "Ocupada Limpia",
    "occupied_dirty": "Ocupada Sucia",
    "cleaning_in_progress": "Limpieza en Progreso",
    "cleaning_completed": "Limpieza Completada",
    "inspected": "Inspeccionada",
    "out_of_service": "Fuera de Servicio",
    "out_of_order": "Fuera de Orden",
    "maintenance_requested": "Mantenimiento Solicitado",
}

ROOM_TRANSITIONS: dict[str, list[str]] = {
    "vacant_dirty": ["cleaning_in_progress", "maintenance_requested"],
    "vacant_clean": ["occupied_clean", "cleaning_in_progress"],
    "occupied_clean": ["occupied_dirty", "vacant_dirty"],
    "occupied_dirty": ["cleaning_in_progress", "vacant_dirty"],
    "cleaning_in_progress": ["cleaning_completed", "maintenance_requested"],
    "cleaning_completed": ["inspected", "cleaning_in_progress", "maintenance_requested"],
    "inspected": ["vacant_clean", "occupied_clean", "maintenance_requested"],
    "out_of_service": ["inspected", "cleaning_in_progress"],
    "out_of_order": ["inspected", "maintenance_requested"],
    "maintenance_requested": ["out_of_service", "out_of_order", "inspected"],
}

ROOM_COLORS: dict[str, str] = {
    "vacant_dirty": "#92400e",
    "vacant_clean": "#16a34a",
    "occupied_clean": "#006076",
    "occupied_dirty": "#d97706",
    "cleaning_in_progress": "#ca8a04",
    "cleaning_completed": "#059669",
    "inspected": "#4338ca",
    "out_of_service": "#6f797d",
    "out_of_order": "#ba1a1a",
    "maintenance_requested": "#ea580c",
}

room_sm = StateMachine(
    name="room",
    states=ROOM_STATES,
    transitions=ROOM_TRANSITIONS,
    colors=ROOM_COLORS,
)


# =============================================================================
#  Invoice status machine
# =============================================================================

INVOICE_STATES: dict[str, str] = {
    "issued": "Emitida",
    "paid": "Pagada",
    "cancelled": "Cancelada",
    "refunded": "Reembolsada",
}

INVOICE_TRANSITIONS: dict[str, list[str]] = {
    "issued": ["paid", "cancelled"],
    "paid": ["refunded"],
    "cancelled": [],
    "refunded": [],
}

INVOICE_COLORS: dict[str, str] = {
    "issued": "#ca8a04",
    "paid": "#16a34a",
    "cancelled": "#ba1a1a",
    "refunded": "#6f797d",
}

invoice_sm = StateMachine(
    name="invoice",
    states=INVOICE_STATES,
    transitions=INVOICE_TRANSITIONS,
    colors=INVOICE_COLORS,
)


# =============================================================================
#  Payment status machine
# =============================================================================

PAYMENT_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "confirmed": "Confirmado",
    "refunded": "Reembolsado",
}

PAYMENT_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["confirmed", "refunded"],
    "confirmed": ["refunded"],
    "refunded": [],
}

PAYMENT_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "confirmed": "#16a34a",
    "refunded": "#6f797d",
}

payment_sm = StateMachine(
    name="payment",
    states=PAYMENT_STATES,
    transitions=PAYMENT_TRANSITIONS,
    colors=PAYMENT_COLORS,
)


# =============================================================================
#  Check-in allowed room statuses (for check-in validation)
# =============================================================================
# These are the room statuses that allow a guest to check in.
CHECKIN_ALLOWED_ROOM_STATUSES = {"vacant_clean", "vacant_dirty"}
CHECKIN_REJECTED_ROOM_STATUSES = {
    s for s in ROOM_STATES if s not in CHECKIN_ALLOWED_ROOM_STATUSES
}

# =============================================================================
#  Housekeeping / Maintenance task status machine
# =============================================================================

TASK_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "in_progress": "En Progreso",
    "completed": "Completada",
    "cancelled": "Cancelada",
}

TASK_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}

TASK_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "in_progress": "#006076",
    "completed": "#16a34a",
    "cancelled": "#6f797d",
}

task_sm = StateMachine(
    name="task",
    states=TASK_STATES,
    transitions=TASK_TRANSITIONS,
    colors=TASK_COLORS,
)


# =============================================================================
#  Service Request (In-Stay) status machine
# =============================================================================
# Lifecycle: pending → in_progress → completed
#                               → cancelled (terminal)

SERVICE_REQUEST_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "in_progress": "En Proceso",
    "completed": "Completado",
    "cancelled": "Cancelado",
}

SERVICE_REQUEST_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}

SERVICE_REQUEST_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "in_progress": "#006076",
    "completed": "#16a34a",
    "cancelled": "#6f797d",
}

service_request_sm = StateMachine(
    name="service_request",
    states=SERVICE_REQUEST_STATES,
    transitions=SERVICE_REQUEST_TRANSITIONS,
    colors=SERVICE_REQUEST_COLORS,
)


# =============================================================================
#  Expense Invoice status machine
# =============================================================================
# Lifecycle: pending → approved → paid
#                   → rejected (terminal)

EXPENSE_INVOICE_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "approved": "Aprobada",
    "rejected": "Rechazada",
    "paid": "Pagada",
}

EXPENSE_INVOICE_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["approved", "rejected"],
    "approved": ["paid"],
    "rejected": [],
    "paid": [],
}

EXPENSE_INVOICE_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "approved": "#006076",
    "rejected": "#ba1a1a",
    "paid": "#16a34a",
}

expense_invoice_sm = StateMachine(
    name="expense_invoice",
    states=EXPENSE_INVOICE_STATES,
    transitions=EXPENSE_INVOICE_TRANSITIONS,
    colors=EXPENSE_INVOICE_COLORS,
)


# =============================================================================
#  Review Moderation status machine
# =============================================================================
# Lifecycle: pending → approved / rejected (both terminal)

REVIEW_MODERATION_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "approved": "Aprobada",
    "rejected": "Rechazada",
}

REVIEW_MODERATION_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["approved", "rejected"],
    "approved": [],
    "rejected": [],
}

REVIEW_MODERATION_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "approved": "#16a34a",
    "rejected": "#ba1a1a",
}

review_moderation_sm = StateMachine(
    name="review_moderation",
    states=REVIEW_MODERATION_STATES,
    transitions=REVIEW_MODERATION_TRANSITIONS,
    colors=REVIEW_MODERATION_COLORS,
)


# =============================================================================
#  Lost Item status machine
# =============================================================================
# Lifecycle: pending → claimed / disposed / returned (all terminal)

LOST_ITEM_STATES: dict[str, str] = {
    "pending": "Pendiente",
    "claimed": "Reclamado",
    "disposed": "Desechado",
    "returned": "Devuelto",
}

LOST_ITEM_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["claimed", "disposed", "returned"],
    "claimed": [],
    "disposed": [],
    "returned": [],
}

LOST_ITEM_COLORS: dict[str, str] = {
    "pending": "#ca8a04",
    "claimed": "#006076",
    "disposed": "#6f797d",
    "returned": "#16a34a",
}

lost_item_sm = StateMachine(
    name="lost_item",
    states=LOST_ITEM_STATES,
    transitions=LOST_ITEM_TRANSITIONS,
    colors=LOST_ITEM_COLORS,
)


# =============================================================================
#  Module-level dict for easy iteration
# =============================================================================

ALL_MACHINES: dict[str, StateMachine] = {
    "booking": booking_sm,
    "stay": stay_sm,
    "room": room_sm,
    "invoice": invoice_sm,
    "payment": payment_sm,
    "task": task_sm,
    "service_request": service_request_sm,
    "expense_invoice": expense_invoice_sm,
    "review_moderation": review_moderation_sm,
    "lost_item": lost_item_sm,
}
