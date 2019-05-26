import os
import sys
import sublime
import sublime_plugin
import io
import gc
import re
import time
from TSL.TSLEngine import *
from TSL.TSLCore import *

class TslCompileCommand(sublime_plugin.WindowCommand):
	panel = False

	def log(self, message, newline='\n'):
		if not newline:
			newline = ''
			
		message = str(message)
		sublime.set_timeout(lambda: self.panel.run_command('append', {'characters': message + newline}), 1)

	def run(self):
		win = sublime.active_window()
		view = win.active_view()
		inlined = False
		vars = win.extract_variables()
		self.panel = win.create_output_panel('tsl', False)

		if 'file' in vars:
			filePath = vars['file']
		else:
			inlined = True
			filePath = view.substr(sublime.Region(0, view.size()))

		win.run_command('show_panel', {"panel": "output.tsl"})

		TSLRunner = TSLEngine(filePath)
		TSLRunner.setLogger(self)

		if TSLRunner.task:
			TSLRunner.data = {}
			timeStart = time.time()
			win.status_message('Running TSL script...')
			TSLRunner.log('Running TSL script "%s"...\n' % ('inline' if inlined else filePath))
			
			if 'file_path' in vars:
				os.chdir(vars['file_path'])

			try:
				TSLRunner.run()
				TSLRunner.log('[Finished in %fs.]' % (time.time() - timeStart));
				win.status_message('Build finished.')
			except Exception as error:
				errorType = sys.exc_info()[0].__name__
				errorMsg = sys.exc_info()[1]
				errorLine = TSLRunner.cmdLine

				TSLRunner.log(' ! %s in line %d: %s' % (errorType, errorLine, errorMsg))
				TSLRunner.log(' ! in command: \t' + TSLRunner.lines[TSLRunner.cmdLine-1])
				TSLRunner.log('_' * 100)
				TSLRunner.log('[Build aborted.]')
				raise

			TSLRunner.data = {}
			gc.collect()
			del TSLRunner