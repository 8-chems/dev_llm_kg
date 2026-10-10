from src.app.pipeline.gate import gate


def test_gate_accept():
    taus = {"resolve": 0.85, "hop": 0.80}
    assert gate("resolve", "c0", 0.90, taus) == "accept"
    assert gate("resolve", "c0", 0.85, taus) == "accept"


def test_gate_escalate_below_tau():
    taus = {"resolve": 0.85, "hop": 0.80}
    assert gate("resolve", "c0", 0.84, taus) == "escalate"


def test_gate_escalate_none_label():
    taus = {"resolve": 0.85}
    assert gate("resolve", "none", 0.99, taus) == "escalate"
    assert gate("resolve", None, 0.99, taus) == "escalate"


def test_gate_missing_tau_escalates():
    taus = {"resolve": 0.85}
    assert gate("unknown_stage", "c0", 0.99, taus) == "escalate"
