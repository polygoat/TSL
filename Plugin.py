import os
import sys
import sublime
import sublime_plugin
import io
import re
import hashlib
from glob import glob
from pprint import pprint
from TSL.TSLEngine import TSLEngine

class TslCompileCommand(sublime_plugin.WindowCommand):
	def run(self):
		vars = self.window.extract_variables()
		filePath = vars['file']

		TSL = TSLEngine(filePath)

		if TSL.task:
			print('Running TSL script "%s"...\n' % filePath)
			os.chdir(vars['file_path'])
			TSL.run()