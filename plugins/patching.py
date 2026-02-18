#------------------------------------------------------------------------------
# Plugin Preflight
#------------------------------------------------------------------------------
#
#    the purpose of this 'preflight' is to test if the plugin is compatible
#    with the environment it is being loaded in. specifically, these preflight
#    checks are designed to be compatible with IDA 7.0+ and Python 2/3
#
#    if the environment does not meet the specifications required by the
#    plugin, this file will gracefully decline to load the plugin without
#    throwing noisy errors (besides a simple print to the IDA console)
#
#    this makes it easy to install the plugin on machines with numerous
#    versions of IDA / Python / virtualenvs which employ a shared plugin
#    directory such as the 'preferred' IDAUSR plugin directory...
#

import os
import sys

# default debug switch for PatchingDBG logs
PATCHING_DEBUG = False

# this plugin requires Python 3
SUPPORTED_PYTHON = sys.version_info[0] == 3

# this plugin requires IDA 7.6 or newer
try:
    import ida_pro
    import ida_idaapi
    IDA_GLOBAL_SCOPE = sys.modules['__main__']
    SUPPORTED_IDA = ida_pro.IDA_SDK_VERSION >= 760
except:
    SUPPORTED_IDA = False

# is this deemed to be a compatible environment for the plugin to load?
SUPPORTED_ENVIRONMENT = bool(SUPPORTED_IDA and SUPPORTED_PYTHON)
if not SUPPORTED_ENVIRONMENT:
    print("Patching plugin is not compatible with this IDA/Python version")

# expose default debug flag into IDA global scope if not already set
if 'IDA_GLOBAL_SCOPE' in globals() and not hasattr(IDA_GLOBAL_SCOPE, 'PATCHING_DEBUG'):
    IDA_GLOBAL_SCOPE.PATCHING_DEBUG = PATCHING_DEBUG

#------------------------------------------------------------------------------
# IDA Plugin Stub
#------------------------------------------------------------------------------

if SUPPORTED_ENVIRONMENT:
    import patching
    from patching.util.python import reload_package

def _debug_enabled():
    """
    Debug logging switch. Defaults to disabled.
    """
    try:
        if hasattr(IDA_GLOBAL_SCOPE, 'PATCHING_DEBUG'):
            return bool(getattr(IDA_GLOBAL_SCOPE, 'PATCHING_DEBUG'))
    except Exception:
        pass

    return os.environ.get('PATCHING_DEBUG', '').strip().lower() in ('1', 'true', 'yes', 'on')

def _dbg(event, **fields):
    """
    Emit lightweight debug diagnostics to the IDA console.
    """
    if not _debug_enabled():
        return

    try:
        seq = getattr(IDA_GLOBAL_SCOPE, '_PATCHING_DEBUG_SEQ', 0) + 1
        IDA_GLOBAL_SCOPE._PATCHING_DEBUG_SEQ = seq
    except Exception:
        seq = -1

    parts = [f"pid={os.getpid()}", f"seq={seq}", f"event={event}", f"file={__file__}"]
    for key in sorted(fields):
        parts.append(f"{key}={fields[key]}")
    print("[PatchingDBG] " + " ".join(parts))

def PLUGIN_ENTRY():
    """
    Required plugin entry point for IDAPython plugins.
    """
    return PatchingPlugin()

class PatchingPlugin(ida_idaapi.plugin_t):
    """
    The IDA Patching plugin stub.
    """

    #
    # Plugin flags:
    # - PLUGIN_PROC: Load / unload this plugin when an IDB opens / closes
    # - PLUGIN_HIDE: Hide this plugin from the IDA plugin menu
    # - PLUGIN_UNL:  Unload the plugin after calling run()
    #

    flags = ida_idaapi.PLUGIN_PROC | ida_idaapi.PLUGIN_HIDE | ida_idaapi.PLUGIN_UNL
    comment = "A plugin to enable binary patching in IDA"
    help = ""
    wanted_name = "Patching"
    wanted_hotkey = ""

    def __init__(self):
        self.__updated = getattr(IDA_GLOBAL_SCOPE, 'RESTART_REQUIRED', False)
        self.core = None
        self._owns_core = False

    #--------------------------------------------------------------------------
    # IDA Plugin Overloads
    #--------------------------------------------------------------------------

    def init(self):
        """
        This is called by IDA when it is loading the plugin.
        """
        _dbg(
            "plugin.init.enter",
            plugin_id=hex(id(self)),
            supported=SUPPORTED_ENVIRONMENT,
            updated=self.__updated
        )

        if not SUPPORTED_ENVIRONMENT or self.__updated:
            _dbg("plugin.init.skip", plugin_id=hex(id(self)))
            return ida_idaapi.PLUGIN_SKIP

        # Reuse an existing core instance if IDA/plugin loader re-enters init().
        existing_core = getattr(IDA_GLOBAL_SCOPE, '_PATCHING_CORE_SINGLETON', None)
        if existing_core is not None:
            self.core = existing_core
            self._owns_core = False
            _dbg(
                "plugin.init.reuse_core",
                plugin_id=hex(id(self)),
                core_id=hex(id(self.core)),
                owns_core=self._owns_core
            )
        else:
            self.core = patching.PatchingCore(defer_load=True)
            self._owns_core = True
            IDA_GLOBAL_SCOPE._PATCHING_CORE_SINGLETON = self.core
            _dbg(
                "plugin.init.new_core",
                plugin_id=hex(id(self)),
                core_id=hex(id(self.core)),
                owns_core=self._owns_core
            )

        # inject a reference to the plugin context into the IDA console scope
        IDA_GLOBAL_SCOPE.patching = self

        # mark the plugin as loaded
        _dbg(
            "plugin.init.keep",
            plugin_id=hex(id(self)),
            core_id=hex(id(self.core)) if self.core else "None",
            owns_core=self._owns_core
        )
        return ida_idaapi.PLUGIN_KEEP

    def run(self, arg):
        """
        This is called by IDA when this file is loaded as a script.
        """
        pass

    def term(self):
        """
        This is called by IDA when it is unloading the plugin.
        """
        _dbg(
            "plugin.term.enter",
            plugin_id=hex(id(self)),
            core_id=hex(id(self.core)) if self.core else "None",
            owns_core=self._owns_core
        )

        if self._owns_core and self.core:
            try:
                self.core.unload()
                _dbg(
                    "plugin.term.core_unloaded",
                    plugin_id=hex(id(self)),
                    core_id=hex(id(self.core))
                )
            except Exception:
                _dbg(
                    "plugin.term.core_unload_error",
                    plugin_id=hex(id(self)),
                    core_id=hex(id(self.core))
                )
                pass

            if getattr(IDA_GLOBAL_SCOPE, '_PATCHING_CORE_SINGLETON', None) is self.core:
                IDA_GLOBAL_SCOPE._PATCHING_CORE_SINGLETON = None

        if getattr(IDA_GLOBAL_SCOPE, 'patching', None) is self:
            IDA_GLOBAL_SCOPE.patching = None

        self.core = None
        self._owns_core = False
        _dbg("plugin.term.exit", plugin_id=hex(id(self)))

    #--------------------------------------------------------------------------
    # Development Helpers
    #--------------------------------------------------------------------------

    def reload(self):
        """
        Hot-reload the plugin.
        """
        _dbg(
            "plugin.reload.enter",
            plugin_id=hex(id(self)),
            core_id=hex(id(self.core)) if self.core else "None",
            owns_core=self._owns_core
        )

        if self.core and self._owns_core:
            self.core.unload()
            _dbg("plugin.reload.unloaded_old_core", plugin_id=hex(id(self)))

        reload_package(patching)
        self.core = patching.PatchingCore()
        self._owns_core = True
        IDA_GLOBAL_SCOPE._PATCHING_CORE_SINGLETON = self.core
        IDA_GLOBAL_SCOPE.patching = self
        _dbg(
            "plugin.reload.new_core",
            plugin_id=hex(id(self)),
            core_id=hex(id(self.core)),
            owns_core=self._owns_core
        )
