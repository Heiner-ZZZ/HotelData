"""Tests for the centralized StateMachine (core/state_machine.py).

Covers:
- Generic StateMachine construction and validation
- Booking status transitions (pending → confirmed → checked_in → checked_out)
- Booking transition rejection (invalid transitions)
- Room (housekeeping) status transitions
- Invoice status transitions (issued → paid → refunded)
- Payment status transitions
- Stay-status (check-in/out) transitions, incl. no-show gerencial reabrible
  (``no_show → pending``, la única salida del no-show tras la feature de
  reapertura) y su documentación de grafo
- Task (housekeeping/maintenance) transitions
- Terminal state detection
- Initial state detection
- to_dict() serialization
"""

from __future__ import annotations

import pytest
from src.app.core.state_machine import (
    StateMachine,
    booking_sm,
    stay_sm,
    room_sm,
    invoice_sm,
    payment_sm,
    task_sm,
    service_request_sm,
    expense_invoice_sm,
    review_moderation_sm,
    lost_item_sm,
    CHECKIN_ALLOWED_ROOM_STATUSES,
    CHECKIN_REJECTED_ROOM_STATUSES,
    ALL_MACHINES,
)


# =============================================================================
#  StateMachine construction tests
# =============================================================================

class TestStateMachineConstruction:
    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name is required"):
            StateMachine(name="", states={"a": "A"}, transitions={"a": ["b"], "b": []})

    def test_rejects_empty_states(self):
        with pytest.raises(ValueError, match="requires at least one state"):
            StateMachine(name="test", states={}, transitions={})

    def test_rejects_empty_transitions(self):
        with pytest.raises(ValueError, match="requires at least one transition"):
            StateMachine(name="test", states={"a": "A"}, transitions={})

    def test_rejects_unknown_source_state(self):
        with pytest.raises(ValueError, match="not a known state"):
            StateMachine(name="test", states={"a": "A"}, transitions={"z": ["a"]})

    def test_rejects_unknown_target_state(self):
        with pytest.raises(ValueError, match="not a known state"):
            StateMachine(name="test", states={"a": "A"}, transitions={"a": ["z"]})


# =============================================================================
#  Generic StateMachine behaviour
# =============================================================================

class TestStateMachineBehaviour:
    def test_can_transition_valid(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta", "c": "Gamma"},
            transitions={"a": ["b"], "b": ["c"], "c": []},
        )
        assert sm.can_transition("a", "b") is True
        assert sm.can_transition("b", "c") is True

    def test_can_transition_invalid(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta", "c": "Gamma"},
            transitions={"a": ["b"], "b": ["c"], "c": []},
        )
        assert sm.can_transition("a", "c") is False
        assert sm.can_transition("c", "a") is False
        assert sm.can_transition("b", "a") is False

    def test_can_transition_unknown_state(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        assert sm.can_transition("z", "a") is False

    def test_validate_transition_valid_does_not_raise(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        sm.validate_transition("a", "b")  # should not raise

    def test_validate_transition_invalid_raises(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta", "c": "Gamma"},
            transitions={"a": ["b"], "b": ["c"], "c": []},
        )
        with pytest.raises(ValueError, match="Transición inválida"):
            sm.validate_transition("a", "c")

    def test_validate_transition_unknown_current(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        with pytest.raises(ValueError, match="Estado actual desconocido"):
            sm.validate_transition("z", "a")

    def test_validate_transition_unknown_target(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        with pytest.raises(ValueError, match="Estado destino desconocido"):
            sm.validate_transition("a", "z")

    def test_validate_transition_terminal_state(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        with pytest.raises(ValueError, match="terminal"):
            sm.validate_transition("b", "a")

    def test_get_valid_next_states(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B", "c": "C"},
            transitions={"a": ["b", "c"], "b": ["c"], "c": []},
        )
        assert sm.get_valid_next_states("a") == ["b", "c"]
        assert sm.get_valid_next_states("b") == ["c"]
        assert sm.get_valid_next_states("c") == []

    def test_get_valid_previous_states(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B", "c": "C"},
            transitions={"a": ["b", "c"], "b": ["c"], "c": []},
        )
        prev_b = sm.get_valid_previous_states("b")
        prev_c = sm.get_valid_previous_states("c")
        assert "a" in prev_b
        assert "a" in prev_c
        assert "b" in prev_c

    def test_get_state_label(self):
        sm = StateMachine(
            name="test",
            states={"a": "Alpha", "b": "Beta"},
            transitions={"a": ["b"], "b": []},
        )
        assert sm.get_state_label("a") == "Alpha"
        assert sm.get_state_label("z") == "z"  # fallback

    def test_get_state_color(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B"},
            transitions={"a": ["b"], "b": []},
            colors={"a": "#ff0000"},
        )
        assert sm.get_state_color("a") == "#ff0000"
        assert sm.get_state_color("b") is None
        assert sm.get_state_color("z") is None

    def test_is_terminal(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B", "c": "C"},
            transitions={"a": ["b"], "b": ["c"], "c": []},
        )
        assert sm.is_terminal("c") is True
        assert sm.is_terminal("a") is False
        assert sm.is_terminal("b") is False

    def test_is_initial(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B", "c": "C"},
            transitions={"a": ["b"], "b": ["c"], "c": []},
        )
        assert sm.is_initial("a") is True
        assert sm.is_initial("b") is False
        assert sm.is_initial("c") is False

    def test_get_all_states_returns_copy(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B"},
            transitions={"a": ["b"], "b": []},
        )
        all_states = sm.get_all_states()
        assert all_states == {"a": "A", "b": "B"}
        # Verify it's a copy
        all_states["c"] = "C"
        assert "c" not in sm.states

    def test_get_all_transitions_returns_copy(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B"},
            transitions={"a": ["b"], "b": []},
        )
        trans = sm.get_all_transitions()
        assert trans == {"a": ["b"], "b": []}
        # Verify it's a copy (modify returned list)
        trans["a"].append("c")
        assert "c" not in sm._transitions["a"]

    def test_to_dict(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B"},
            transitions={"a": ["b"], "b": []},
            colors={"a": "#ff0000", "b": "#00ff00"},
        )
        d = sm.to_dict()
        assert d["name"] == "test"
        assert d["states"] == {"a": "A", "b": "B"}
        assert d["transitions"] == {"a": ["b"], "b": []}
        assert d["colors"] == {"a": "#ff0000", "b": "#00ff00"}
        assert "b" in d["terminal_states"]
        assert "a" in d["initial_states"]

    def test_immutable_after_construction(self):
        sm = StateMachine(
            name="test",
            states={"a": "A", "b": "B"},
            transitions={"a": ["b"], "b": []},
        )
        # Verify defensive copy - modifying returned get_all_states() doesn't affect original
        returned = sm.get_all_states()
        original = dict(sm.states)
        returned["c"] = "C"
        assert sm.states == original, "Mutating returned dict should not affect internal states"
        assert "c" not in sm.states


# =============================================================================
#  Booking StateMachine tests
# =============================================================================

class TestBookingStateMachine:
    def test_pending_can_transition(self):
        """pending → confirmed, rejected, cancelled"""
        assert booking_sm.can_transition("pending", "confirmed") is True
        assert booking_sm.can_transition("pending", "rejected") is True
        assert booking_sm.can_transition("pending", "cancelled") is True

    def test_pending_cannot_skip_states(self):
        """pending cannot jump to checked_in or checked_out"""
        assert booking_sm.can_transition("pending", "checked_in") is False
        assert booking_sm.can_transition("pending", "checked_out") is False

    def test_confirmed_can_transition(self):
        """confirmed → checked_in, cancelled"""
        assert booking_sm.can_transition("confirmed", "checked_in") is True
        assert booking_sm.can_transition("confirmed", "cancelled") is True

    def test_confirmed_cannot_go_back(self):
        """confirmed cannot go back to pending or rejected"""
        assert booking_sm.can_transition("confirmed", "pending") is False
        assert booking_sm.can_transition("confirmed", "rejected") is False

    def test_full_lifecycle_valid(self):
        """pending → confirmed → checked_in → checked_out"""
        assert booking_sm.can_transition("pending", "confirmed") is True
        assert booking_sm.can_transition("confirmed", "checked_in") is True
        assert booking_sm.can_transition("checked_in", "checked_out") is True

    def test_terminal_states(self):
        """rejected, cancelled, checked_out are terminal"""
        assert booking_sm.is_terminal("rejected") is True
        assert booking_sm.is_terminal("cancelled") is True
        assert booking_sm.is_terminal("checked_out") is True
        assert booking_sm.is_terminal("pending") is False
        assert booking_sm.is_terminal("confirmed") is False

    def test_transition_with_state_machine(self):
        """confirm_booking and reject_booking should work with central validation"""
        # The _transition_status function now uses booking_sm.validate_transition()
        # which should validate correctly:
        booking_sm.validate_transition("pending", "confirmed")  # OK
        booking_sm.validate_transition("pending", "rejected")   # OK
        booking_sm.validate_transition("confirmed", "checked_in")  # OK
        booking_sm.validate_transition("checked_in", "checked_out")  # OK

    def test_invalid_transitions_raise(self):
        with pytest.raises(ValueError, match="Transición inválida"):
            booking_sm.validate_transition("confirmed", "pending")
        with pytest.raises(ValueError, match="terminal"):
            booking_sm.validate_transition("rejected", "confirmed")
        with pytest.raises(ValueError, match="terminal"):
            booking_sm.validate_transition("cancelled", "confirmed")
        with pytest.raises(ValueError, match="terminal"):
            booking_sm.validate_transition("checked_out", "checked_in")


# =============================================================================
#  Stay-status StateMachine tests
# =============================================================================

class TestStayStateMachine:
    """Grafo de Stay-status (ortogonal a ``booking.status``):

    ::

        pending ──► checked_in ──► checked_out (terminal)
           │
           └──► no_show ──► pending   # reapertura gerencial (no-show reabrible)

    Desde la feature de reapertura de no-show, ``no_show`` YA NO es un
    estado terminal: el gerente (``check-ins.no_show_reopen``) puede
    reabrir la reserva y devolverla a ``pending`` para el check-in normal.
    La única salida de ``no_show`` es esa reapertura.
    """

    def test_pending_can_check_in(self):
        assert stay_sm.can_transition("pending", "checked_in") is True
        assert stay_sm.can_transition("pending", "no_show") is True

    def test_checked_in_can_check_out(self):
        assert stay_sm.can_transition("checked_in", "checked_out") is True

    def test_checked_out_is_terminal(self):
        assert stay_sm.is_terminal("checked_out") is True

    def test_no_show_is_not_terminal_anymore(self):
        """Tras la feature de reapertura, el no-show tiene salida
        (``no_show → pending``): ya no es un estado terminal."""
        assert stay_sm.is_terminal("no_show") is False

    def test_no_show_can_be_reopened_to_pending(self):
        """La reapertura gerencial es la ÚNICA salida de ``no_show``."""
        assert stay_sm.can_transition("no_show", "pending") is True
        assert stay_sm.get_valid_next_states("no_show") == ["pending"]
        assert "pending" in stay_sm.get_valid_previous_states("no_show")

    def test_no_show_cannot_transition_elsewhere(self):
        """El no-show no puede saltar directo a check-in/out ni reabrirse
        desde otro estado: el único camino de vuelta es pending."""
        assert stay_sm.can_transition("no_show", "checked_in") is False
        assert stay_sm.can_transition("no_show", "checked_out") is False
        assert stay_sm.can_transition("checked_in", "no_show") is False
        assert stay_sm.can_transition("checked_out", "no_show") is False
        assert stay_sm.can_transition("checked_out", "pending") is False

    def test_reopen_transition_validates_without_raising(self):
        """``no_show → pending`` pasa la validación central; cualquier otra
        salida desde un terminal (checked_out) sigue rechazada."""
        stay_sm.validate_transition("no_show", "pending")  # no raise
        with pytest.raises(ValueError, match="terminal"):
            stay_sm.validate_transition("checked_out", "no_show")

    def test_cannot_skip_to_checkout(self):
        assert stay_sm.can_transition("pending", "checked_out") is False


# =============================================================================
#  Room (housekeeping) StateMachine tests
# =============================================================================

class TestRoomStateMachine:
    def test_vacant_dirty_transitions(self):
        """vacant_dirty → cleaning_in_progress, maintenance_requested"""
        assert room_sm.can_transition("vacant_dirty", "cleaning_in_progress") is True
        assert room_sm.can_transition("vacant_dirty", "maintenance_requested") is True
        assert room_sm.can_transition("vacant_dirty", "vacant_clean") is False  # needs cleaning first

    def test_full_cleaning_cycle(self):
        """vacant_dirty → cleaning_in_progress → cleaning_completed → inspected → vacant_clean"""
        assert room_sm.can_transition("vacant_dirty", "cleaning_in_progress") is True
        assert room_sm.can_transition("cleaning_in_progress", "cleaning_completed") is True
        assert room_sm.can_transition("cleaning_completed", "inspected") is True
        assert room_sm.can_transition("inspected", "vacant_clean") is True

    def test_occupied_transitions(self):
        """occupied_clean → occupied_dirty, vacant_dirty"""
        assert room_sm.can_transition("occupied_clean", "occupied_dirty") is True
        assert room_sm.can_transition("occupied_clean", "vacant_dirty") is True
        assert room_sm.can_transition("occupied_clean", "vacant_clean") is False

    def test_maintenance_flow(self):
        """Any state → maintenance_requested → out_of_service/out_of_order → inspected"""
        assert room_sm.can_transition("vacant_clean", "occupied_clean") is True
        assert room_sm.can_transition("maintenance_requested", "out_of_service") is True
        assert room_sm.can_transition("maintenance_requested", "out_of_order") is True
        assert room_sm.can_transition("out_of_service", "inspected") is True
        assert room_sm.can_transition("out_of_order", "inspected") is True

    def test_labels_spanish(self):
        assert room_sm.get_state_label("vacant_dirty") == "Vacante Sucia"
        assert room_sm.get_state_label("vacant_clean") == "Vacante Limpia"
        assert room_sm.get_state_label("occupied_clean") == "Ocupada Limpia"

    def test_colors_exist(self):
        assert room_sm.get_state_color("vacant_dirty") == "#92400e"
        assert room_sm.get_state_color("vacant_clean") == "#16a34a"

    def test_checkin_allowed_statuses(self):
        assert "vacant_clean" in CHECKIN_ALLOWED_ROOM_STATUSES
        assert "vacant_dirty" in CHECKIN_ALLOWED_ROOM_STATUSES
        assert "occupied_clean" not in CHECKIN_ALLOWED_ROOM_STATUSES
        assert "out_of_order" not in CHECKIN_ALLOWED_ROOM_STATUSES

    def test_checkin_rejected_statuses_are_complement(self):
        all_room_states = set(room_sm.states)
        assert CHECKIN_ALLOWED_ROOM_STATUSES | CHECKIN_REJECTED_ROOM_STATUSES == all_room_states
        assert CHECKIN_ALLOWED_ROOM_STATUSES & CHECKIN_REJECTED_ROOM_STATUSES == set()


# =============================================================================
#  Invoice StateMachine tests
# =============================================================================

class TestInvoiceStateMachine:
    def test_issued_can_transition(self):
        """issued → paid, cancelled"""
        assert invoice_sm.can_transition("issued", "paid") is True
        assert invoice_sm.can_transition("issued", "cancelled") is True

    def test_paid_can_refund(self):
        """paid → refunded"""
        assert invoice_sm.can_transition("paid", "refunded") is True

    def test_cannot_go_back(self):
        assert invoice_sm.can_transition("paid", "issued") is False
        assert invoice_sm.can_transition("cancelled", "issued") is False
        assert invoice_sm.can_transition("refunded", "paid") is False

    def test_terminal_states(self):
        assert invoice_sm.is_terminal("cancelled") is True
        assert invoice_sm.is_terminal("refunded") is True
        assert invoice_sm.is_terminal("issued") is False
        assert invoice_sm.is_terminal("paid") is False

    def test_labels_spanish(self):
        assert invoice_sm.get_state_label("issued") == "Emitida"
        assert invoice_sm.get_state_label("paid") == "Pagada"
        assert invoice_sm.get_state_label("cancelled") == "Cancelada"
        assert invoice_sm.get_state_label("refunded") == "Reembolsada"


# =============================================================================
#  Payment StateMachine tests
# =============================================================================

class TestPaymentStateMachine:
    def test_pending_can_confirm(self):
        """pending → confirmed"""
        assert payment_sm.can_transition("pending", "confirmed") is True

    def test_confirmed_can_refund(self):
        """confirmed → refunded"""
        assert payment_sm.can_transition("confirmed", "refunded") is True

    def test_cannot_go_back(self):
        assert payment_sm.can_transition("confirmed", "pending") is False
        assert payment_sm.can_transition("refunded", "confirmed") is False

    def test_terminal_states(self):
        assert payment_sm.is_terminal("refunded") is True
        assert payment_sm.is_terminal("pending") is False
        assert payment_sm.is_terminal("confirmed") is False

    def test_labels_spanish(self):
        assert payment_sm.get_state_label("pending") == "Pendiente"
        assert payment_sm.get_state_label("confirmed") == "Confirmado"
        assert payment_sm.get_state_label("refunded") == "Reembolsado"


# =============================================================================
#  Task StateMachine tests
# =============================================================================

class TestTaskStateMachine:
    def test_pending_transitions(self):
        """pending → in_progress, cancelled"""
        assert task_sm.can_transition("pending", "in_progress") is True
        assert task_sm.can_transition("pending", "cancelled") is True

    def test_in_progress_transitions(self):
        """in_progress → completed, cancelled"""
        assert task_sm.can_transition("in_progress", "completed") is True
        assert task_sm.can_transition("in_progress", "cancelled") is True

    def test_terminal_states(self):
        assert task_sm.is_terminal("completed") is True
        assert task_sm.is_terminal("cancelled") is True

    def test_labels_spanish(self):
        assert task_sm.get_state_label("pending") == "Pendiente"
        assert task_sm.get_state_label("in_progress") == "En Progreso"
        assert task_sm.get_state_label("completed") == "Completada"
        assert task_sm.get_state_label("cancelled") == "Cancelada"


# =============================================================================
#  Service Request StateMachine tests
# =============================================================================

class TestServiceRequestStateMachine:
    def test_pending_transitions(self):
        """pending → in_progress, cancelled"""
        assert service_request_sm.can_transition("pending", "in_progress") is True
        assert service_request_sm.can_transition("pending", "cancelled") is True

    def test_in_progress_transitions(self):
        """in_progress → completed, cancelled"""
        assert service_request_sm.can_transition("in_progress", "completed") is True
        assert service_request_sm.can_transition("in_progress", "cancelled") is True

    def test_terminal_states(self):
        assert service_request_sm.is_terminal("completed") is True
        assert service_request_sm.is_terminal("cancelled") is True

    def test_labels_spanish(self):
        assert service_request_sm.get_state_label("pending") == "Pendiente"
        assert service_request_sm.get_state_label("in_progress") == "En Proceso"
        assert service_request_sm.get_state_label("completed") == "Completado"
        assert service_request_sm.get_state_label("cancelled") == "Cancelado"


# =============================================================================
#  Expense Invoice StateMachine tests
# =============================================================================

class TestExpenseInvoiceStateMachine:
    def test_pending_transitions(self):
        """pending → approved, rejected"""
        assert expense_invoice_sm.can_transition("pending", "approved") is True
        assert expense_invoice_sm.can_transition("pending", "rejected") is True

    def test_approved_can_pay(self):
        """approved → paid"""
        assert expense_invoice_sm.can_transition("approved", "paid") is True

    def test_cannot_go_back(self):
        assert expense_invoice_sm.can_transition("approved", "pending") is False
        assert expense_invoice_sm.can_transition("rejected", "approved") is False
        assert expense_invoice_sm.can_transition("paid", "approved") is False

    def test_terminal_states(self):
        assert expense_invoice_sm.is_terminal("rejected") is True
        assert expense_invoice_sm.is_terminal("paid") is True
        assert expense_invoice_sm.is_terminal("pending") is False

    def test_labels_spanish(self):
        assert expense_invoice_sm.get_state_label("pending") == "Pendiente"
        assert expense_invoice_sm.get_state_label("approved") == "Aprobada"
        assert expense_invoice_sm.get_state_label("rejected") == "Rechazada"
        assert expense_invoice_sm.get_state_label("paid") == "Pagada"


# =============================================================================
#  Review Moderation StateMachine tests
# =============================================================================

class TestReviewModerationStateMachine:
    def test_pending_transitions(self):
        """pending → approved, rejected"""
        assert review_moderation_sm.can_transition("pending", "approved") is True
        assert review_moderation_sm.can_transition("pending", "rejected") is True

    def test_terminal_states(self):
        assert review_moderation_sm.is_terminal("approved") is True
        assert review_moderation_sm.is_terminal("rejected") is True
        assert review_moderation_sm.is_terminal("pending") is False

    def test_cannot_go_back(self):
        assert review_moderation_sm.can_transition("approved", "pending") is False
        assert review_moderation_sm.can_transition("rejected", "approved") is False

    def test_labels_spanish(self):
        assert review_moderation_sm.get_state_label("pending") == "Pendiente"
        assert review_moderation_sm.get_state_label("approved") == "Aprobada"
        assert review_moderation_sm.get_state_label("rejected") == "Rechazada"


# =============================================================================
#  Lost Item StateMachine tests
# =============================================================================

class TestLostItemStateMachine:
    def test_pending_transitions(self):
        """pending → claimed, disposed, returned"""
        assert lost_item_sm.can_transition("pending", "claimed") is True
        assert lost_item_sm.can_transition("pending", "disposed") is True
        assert lost_item_sm.can_transition("pending", "returned") is True

    def test_terminal_states(self):
        assert lost_item_sm.is_terminal("claimed") is True
        assert lost_item_sm.is_terminal("disposed") is True
        assert lost_item_sm.is_terminal("returned") is True
        assert lost_item_sm.is_terminal("pending") is False

    def test_cannot_go_back(self):
        assert lost_item_sm.can_transition("claimed", "pending") is False
        assert lost_item_sm.can_transition("returned", "disposed") is False

    def test_labels_spanish(self):
        assert lost_item_sm.get_state_label("pending") == "Pendiente"
        assert lost_item_sm.get_state_label("claimed") == "Reclamado"
        assert lost_item_sm.get_state_label("disposed") == "Desechado"
        assert lost_item_sm.get_state_label("returned") == "Devuelto"


# =============================================================================
#  ALL_MACHINES dict
# =============================================================================

class TestAllMachines:
    def test_all_machines_are_accessible(self):
        assert len(ALL_MACHINES) == 10
        assert "booking" in ALL_MACHINES
        assert "stay" in ALL_MACHINES
        assert "room" in ALL_MACHINES
        assert "invoice" in ALL_MACHINES
        assert "payment" in ALL_MACHINES
        assert "task" in ALL_MACHINES

    def test_each_machine_has_name(self):
        for name, sm in ALL_MACHINES.items():
            assert sm.name == name
            assert len(sm.states) >= 2

    def test_each_machine_has_no_dead_ends(self):
        """All defined states must appear in transitions dict (as source or target)."""
        for name, sm in ALL_MACHINES.items():
            all_sources = set(sm._transitions)
            all_targets = set()
            for targets in sm._transitions.values():
                all_targets.update(targets)
            # Every state must either be a source or a target
            for state in sm.states:
                assert state in all_sources or state in all_targets, (
                    f"State '{state}' in machine '{name}' is unreachable and has no transitions"
                )
