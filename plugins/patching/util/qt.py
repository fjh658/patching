"""
Qt compatibility helpers shared across the plugin.
"""

QT_AVAILABLE = False
QT_LIB = None         # Qt major version (5/6)
QT_BINDING = None     # PyQt5 / PyQt6 / PySide6 / ...

QtCore = None
QtGui = None
QtWidgets = None

qt_wrapinstance = None

def _init_pyqt5():
    global QtCore, QtGui, QtWidgets, QT_LIB, QT_BINDING, qt_wrapinstance
    from PyQt5 import QtCore as _QtCore
    from PyQt5 import QtGui as _QtGui
    from PyQt5 import QtWidgets as _QtWidgets
    from PyQt5 import sip as _sip
    QtCore, QtGui, QtWidgets = _QtCore, _QtGui, _QtWidgets
    QT_LIB = 5
    QT_BINDING = 'PyQt5'
    qt_wrapinstance = lambda ptr, cls: _sip.wrapinstance(int(ptr), cls)

def _init_pyqt6():
    global QtCore, QtGui, QtWidgets, QT_LIB, QT_BINDING, qt_wrapinstance
    from PyQt6 import QtCore as _QtCore
    from PyQt6 import QtGui as _QtGui
    from PyQt6 import QtWidgets as _QtWidgets
    try:
        from PyQt6 import sip as _sip
    except ImportError:
        import sip as _sip
    QtCore, QtGui, QtWidgets = _QtCore, _QtGui, _QtWidgets
    QT_LIB = 6
    QT_BINDING = 'PyQt6'
    qt_wrapinstance = lambda ptr, cls: _sip.wrapinstance(int(ptr), cls)

def _init_pyside6():
    global QtCore, QtGui, QtWidgets, QT_LIB, QT_BINDING, qt_wrapinstance
    from PySide6 import QtCore as _QtCore
    from PySide6 import QtGui as _QtGui
    from PySide6 import QtWidgets as _QtWidgets
    from shiboken6 import wrapInstance as _wrapInstance
    QtCore, QtGui, QtWidgets = _QtCore, _QtGui, _QtWidgets
    QT_LIB = 6
    QT_BINDING = 'PySide6'
    qt_wrapinstance = lambda ptr, cls: _wrapInstance(int(ptr), cls)

# attempt to load PyQt5 first (for older IDA), then PyQt6, then PySide6 (IDA 9.2)
for initializer in (_init_pyqt5, _init_pyqt6, _init_pyside6):
    if QT_BINDING:
        break
    try:
        initializer()
    except ImportError:
        continue
    except Exception:
        continue

QT_AVAILABLE = bool(QT_BINDING)

#--------------------------------------------------------------------------
# PyQt Compatibility
#--------------------------------------------------------------------------

def _alias(namespace, name, value):
    if namespace and not hasattr(namespace, name):
        setattr(namespace, name, value)

if QT_AVAILABLE and QT_LIB == 6:
    # Alignments
    _alias(QtCore.Qt, 'AlignRight', QtCore.Qt.AlignmentFlag.AlignRight)
    _alias(QtCore.Qt, 'AlignVCenter', QtCore.Qt.AlignmentFlag.AlignVCenter)
    _alias(QtCore.Qt, 'AlignTop', QtCore.Qt.AlignmentFlag.AlignTop)
    _alias(QtCore.Qt, 'AlignHCenter', QtCore.Qt.AlignmentFlag.AlignHCenter)

    # Window flags
    _alias(QtCore.Qt, 'WindowSystemMenuHint', QtCore.Qt.WindowType.WindowSystemMenuHint)
    _alias(QtCore.Qt, 'WindowContextHelpButtonHint', QtCore.Qt.WindowType.WindowContextHelpButtonHint)
    _alias(QtCore.Qt, 'MSWindowsFixedSizeDialogHint', QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint)

    # Keyboard constants
    _alias(QtCore.Qt, 'Key_Down', QtCore.Qt.Key.Key_Down)
    _alias(QtCore.Qt, 'Key_Up', QtCore.Qt.Key.Key_Up)

    # QEvent types
    if hasattr(QtCore, 'QEvent') and hasattr(QtCore.QEvent, 'Type'):
        _alias(QtCore.QEvent, 'Polish', QtCore.QEvent.Type.Polish)

    # QFont style hints
    if hasattr(QtGui, 'QFont') and hasattr(QtGui.QFont, 'StyleHint'):
        _alias(QtGui.QFont, 'Monospace', QtGui.QFont.StyleHint.Monospace)

#--------------------------------------------------------------------------
# Qt Misc Helpers
#--------------------------------------------------------------------------

def get_main_window():
    """
    Return the Qt Main Window.
    """
    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMainWindow):
            return widget
    return None

def center_widget(widget):
    """
    Center the given widget to the Qt Main Window.
    """
    main_window = get_main_window()
    if not main_window:
        return False

    #
    # compute a new position for the floating widget such that it will center
    # over the Qt application's main window
    #

    rect_main = main_window.geometry()
    rect_widget = widget.rect()

    centered_position = rect_main.center() - rect_widget.center()
    widget.move(centered_position)

    return True
