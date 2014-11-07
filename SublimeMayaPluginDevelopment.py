"""@date 2014/09/10
@brief Plugin for maya plugin development
@details Sends the current maya plugin together with user defined code
         to maya.
@author Paul Schweizer
@email paulschweizer@gmx.net
"""

import os
import re
import sys
import time
import textwrap
from telnetlib import Telnet
import sublime
import sublime_plugin


class TestMayaPluginCommand(sublime_plugin.TextCommand):

    """Sends the current maya plugin together with user defined code to
    maya.
    @todo Modify the MayaSublime plugin in a way to be able to use it.
    @todo Optimize some var retrievals

    """

    def __init__(self, view):
        """Initializes variables for the class."""
        self._platform = self._get_platform()
        self.view = view
    # END def __init__

    def _get_platform(self):
        """Returns the current operating system
        @todo implement for OSX

        """
        platform = sys.platform
        if 'linux' in platform:
            return 'linux'
        elif 'windows' in platform:
            return 'windows'
        # END if
    # END def _get_platform

    def run(self, edit):
        """The run method to execute the plugin testing.
        First builds the execution string:
        1. get the plugin path
        2. unload plugin
        3. load plugin
        4. add additional code, found in the .sublime-settings file
            creation_code:{
                "name_of_plugin": {
                    "platform": "X64",
                    "file": "path/to/file/with/code.py"
                    "code": "plain_python_code()"
                }
            }

        """
        name = os.path.basename(os.path.dirname(self.view.file_name()))
        plugin_settings = self.settings.get('plugins')[name]
        plugin_path = self._plugin_path(plugin_settings)
        custom_code = plugin_settings['code']
        if isinstance(custom_code, list):
            custom_code = ''.join(custom_code)
        # END if

        command = ('from maya import cmds, mel;'
                   'cmds.unloadPlugin("%s", f=True);'
                   'cmds.loadPlugin("%s");'
                   '%s' % (name, plugin_path, custom_code))
        self.run_plugin_command(command)
    # END def run

    @property
    def settings(self):
        """Retrieves the settings.
        @return the settings

        """
        return sublime.load_settings('SublimeMayaPluginDevelopment.sublime-settings')
    # END def settings

    def _plugin_path(self, plugin_settings):
        """Concatenates and returns the plugin path based on the
        operating system.

        """
        name = os.path.basename(os.path.dirname(self.view.file_name()))
        base = os.path.dirname(self.view.file_name())
        file_ending = self.settings.get('file_endings')[self._platform]
        if self._platform == 'linux':
            return os.path.join(base, '%s.%s' % (name, file_ending))
        elif self._platform == 'windows':
            return os.path.join(base, plugin_settings['platform'], 'Debug',
                                '%s.%s' % (name, file_ending))
        # END if
    # END def _plugin_path

    def run_plugin_command(self, command):
        """Runs the given command in maya to test the plugin.
        @param command the command to send to maya
        @todo properly format the string for the exec

        """
        PY_CMD_TEMPLATE = textwrap.dedent('''
            import traceback
            import __main__

            namespace = __main__.__dict__.get('_sublime_SendToMaya_plugin')
            if not namespace:
                namespace = __main__.__dict__.copy()
                __main__.__dict__['_sublime_SendToMaya_plugin'] = namespace

            namespace['__file__'] = {2!r}

            try:
                {0}({1!r}, namespace, namespace)
            except:
                traceback.print_exc()
        ''')

        # Match single-line comments in MEL/Python
        RX_COMMENT = re.compile(r'^\s*(//|#)')

        host = self.settings.get('host')
        port = self.settings.get('port')

        print('Sending {0}:\n{1!r}\n...'.format('python', command[:200]))

        command = PY_CMD_TEMPLATE.format('exec',
                                         command.replace('\\r', '\\\\r'), '')
        c = None

        try:
            c = Telnet(host, int(port), timeout=3)
            c.write(command.encode(encoding='UTF-8'))
        except Exception:
            e = sys.exc_info()[1]
            err = str(e)
            sublime.error_message('Failed to communicate with Maya'
                                  ' (%(host)s:%(port)s)):\n%(err)s' % locals())
            raise
        else:
            time.sleep(0.1)
        finally:
            if c is not None:
                c.close()
            # END if
        # END try
    # END def run_plugin_command
# END class TestMayaPluginCommand


class UnloadMayaPluginCommand(TestMayaPluginCommand):

    """Unloads the current plugin in maya, so it can be rebuilt."""

    def run(self, edit):
        """Builds the command to unload the current plugin in maya."""
        name = os.path.basename(os.path.dirname(self.view.file_name()))
        plugin_path = self._plugin_path(self.settings.get('plugins')[name])
        command = ('from maya import cmds, mel;'
                   'cmds.unloadPlugin("%(name)s", f=True);' % locals())
        self.run_plugin_command(command)
    # END def run
# END class UnloadMayaPluginCommand
