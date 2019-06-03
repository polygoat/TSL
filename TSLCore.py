import io
import os
import re
import hashlib
import sys
from .glob2 import glob
from TSL.TSLHelpers import *

class TSLLogger:
	def log(self, whatever, ignore=''):
		return print(whatever)

class TSLCore:
	__logger = TSLLogger()
	__plurals = {}

	active = True
	verbose = False

	plugins = {}
	parsers = {}
	hooks = {}

	cmdLine = 0
	fileName = ''
	task = ''

	lines = {}

	def __init__(self, taskFilePath=False):
		TSLData.reset()

		if taskFilePath:
			taskFilePath = taskFilePath.strip()
			if taskFilePath.endswith('.tsl'):
				self.fileName = taskFilePath
				with io.open(taskFilePath, 'r', encoding='utf8') as taskFile:
					self.task = taskFile.read()
			elif taskFilePath.endswith('.py'):
				self.log('! You are trying to run a Python script using TSL. Please change your Tools > Build System to Python')
			elif taskFilePath.startswith('{') and taskFilePath.endswith('}'):
				self.task = taskFilePath
			else:
				self.log('! %s is not a valid task file.' % taskFilePath)
	
	def __isRaw(self, anyString):
		return anyString.startswith('/') and anyString.endswith('/')

	def setLogger(self, container):
		self.__logger = container
		return self

	def log(self, message, newline='\n'):
		self.__logger.log(message, newline)
		return self

	def registerPlugin(self, name, method):
		self.plugins[name] = method
		return self

	def registerParser(self, extension, method):
		self.parsers[extension] = method
		return self

	def isActive(self):
		return self.active

	def pluck(self, dict, *args):
		return [dict[arg] for arg in args]

	def toPlural(self, word):
		plural = self.__plurals.get(word)
		if not plural:
			plural = TSLInflector.plural(word)
			self.__plurals[word] = plural
		return plural

	def fromPlural(self, word):
		if word in self.__plurals:
			__singulars = {value: key for key, value in self.__plurals.items()}
			singular = __singulars[word]
		else:
			singular = TSLInflector.singular(word)
			self.__plurals[singular] = word
		return singular

	def resolveAsClause(self, varName, value):
		TSLData[varName] = value

		if self.looping:
			if varName != 'selection':
				plural = self.toPlural(varName)
				if plural != varName:
					collection = TSLData[plural,False]

					if collection:
						collection.append(value)
					else:
						collection = [value]
					TSLData[plural] = collection

	@tail_recursive
	def runLine(self, cmdLine):
		command = self.lines[cmdLine].strip()
		self.cmdLine = cmdLine + 1

		command = re.findall(r'(?:\".*?[^\\\\]\"|\S)+', command)

		if len(command) and not command[0].startswith('#'):
			if command[0][0:3] == '---':
				command[0] = 'repeat'

			self.executeCommand(command)

		if self.isActive() and self.cmdLine < len(self.lines):
			recurse(self, self.cmdLine) 

	def executeCommand(self, command):
		if hasattr(self, '_' + command[0]):
				eval('self._' + command[0])(command[1:])
		elif command[0] in self.plugins:
			self.plugins[command[0]](command[1:])
		else:
			self.log(' !' + command[0] + ' is no valid command !')

	def parse(self, task):
		isTask = re.findall(r'\{[\n\s]*([\w\W]+)[\n\s]*\}', task)

		if len(isTask):
			return re.split(r'\s*[\n\r]\s*', isTask[0])

		self.log(' ! No viable task found.')
		return False

	def run(self):
		task = self.parse(self.task)
		TSLData.reset()

		if task:
			self.lines = task
			self.runLine(0)
			self.log('')
		
		return self