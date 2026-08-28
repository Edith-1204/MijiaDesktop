from app.workers.base_worker import Worker


def test_worker_emits_result_and_finished():
    worker = Worker(lambda left, right: left + right, 2, 3)
    results = []
    finished = []
    worker.signals.result.connect(results.append)
    worker.signals.finished.connect(lambda: finished.append(True))
    worker.run()
    assert results == [5]
    assert finished == [True]


def test_worker_converts_exception_to_error_signal():
    worker = Worker(lambda: 1 / 0)
    errors = []
    worker.signals.error.connect(errors.append)
    worker.run()
    assert len(errors) == 1
    assert isinstance(errors[0], ZeroDivisionError)

