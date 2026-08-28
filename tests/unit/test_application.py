from app import __version__
from app.application import create_application, load_application_icon
from app.ui.style import load_stylesheet
from app.ui.main_window import MainWindow


def test_application_metadata(qapp):
    application = create_application([])

    assert application.applicationName() == "Mijia Desktop"
    assert application.applicationVersion() == __version__
    assert not application.windowIcon().isNull()


def test_application_icon_is_available():
    icon = load_application_icon()

    assert not icon.isNull()
    assert icon.availableSizes()


def test_search_style_keeps_typed_text_readable():
    stylesheet = load_stylesheet()
    assert "QLineEdit#deviceSearch" in stylesheet
    assert "color: #202124" in stylesheet
    assert "placeholder-text-color: #7a828b" in stylesheet


def test_combo_popup_text_is_readable_in_both_themes():
    light = load_stylesheet("light")
    dark = load_stylesheet("dark")

    assert "QComboBox QAbstractItemView" in light
    assert "background: #ffffff; color: #202124" in light
    assert "background: #25292e; color: #f1f3f4" in dark


def test_device_detail_background_is_defined_in_both_themes():
    light = load_stylesheet("light")
    dark = load_stylesheet("dark")

    for selector in (
        "QWidget#deviceDetailPage",
        "QTabWidget#detailTabs",
        "QScrollArea#detailScroll",
        "QWidget#detailViewport",
        "QWidget#detailContent",
        "QWidget#deviceInfo",
    ):
        assert selector in light
        assert selector in dark
    assert "QTabWidget::pane { border: none; background: #f4f6f8; }" in light
    assert "QTabWidget::pane { background: #17191c; }" in dark


def test_main_window_can_be_created(qapp):
    window = MainWindow()

    assert window.windowTitle() == "Mijia Desktop"
    assert not window.windowIcon().isNull()
    assert window.minimumWidth() == 760
    assert window.minimumHeight() == 520
