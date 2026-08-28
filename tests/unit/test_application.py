from app import __version__
from app.application import create_application
from app.ui.main_window import MainWindow


def test_application_metadata(qapp):
    application = create_application([])

    assert application.applicationName() == "Mijia Desktop"
    assert application.applicationVersion() == __version__


def test_main_window_can_be_created(qapp):
    window = MainWindow()

    assert window.windowTitle() == "Mijia Desktop"
    assert window.minimumWidth() == 720
    assert window.minimumHeight() == 480

