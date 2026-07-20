from app.jobs.tasks import _best_effort


def test_best_effort_swallows_exceptions():
    def boom():
        raise RuntimeError("broker unreachable")

    # Must not raise: job scheduling is a side effect of an already-committed
    # transaction and can never turn a successful request into a 500.
    _best_effort("test action", boom)


def test_best_effort_runs_the_function():
    calls = []
    _best_effort("test action", lambda: calls.append(1))
    assert calls == [1]
