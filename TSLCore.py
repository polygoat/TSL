import io
import os
import re
import hashlib
import sys
from glob import glob
from pprint import pprint

class TaskRunnerArgs(dict):
	def __init__(self, args, defaults={}):
		self.arguments = []
		self.parsed = {}
		self.referenced = {}
		self.literals = []
		self.clauses = []

		self.update(defaults)
		for k,v in defaults.items():
			if k not in defaults:
				args.append(k)
				args.append(v)

	def __clean(self, anyString):
		try: 	anyString = str(anyString)
		except: pass

		if anyString.startswith('"') and anyString.endswith('"'):
			anyString = anyString[1:-1]

		return anyString

	def __renderProps(self, props, delimiter=' '):
		propList = []

		for k,v in props.items():
			k = self.__clean(k)
			v = self.__clean(v)
			if len(v) > 20:
				v = v[0:20] + '...' + v[-6:-1]

			propList.append('%s=%s' % (k, v))

		return delimiter.join(propList)

	def findRef(self, reference):
		for ref, value in self.referenced.items():
			if value == reference:
				return ref
		return False

	def __str__(self):
		return '<TaskRunnerArguments\n\t%s\n\treferenced[%s]\n\tliterals%s\n\tparsed[%s]\n/>' % (self.__renderProps(self, '\n\t'), self.__renderProps(self.referenced, ' '), self.literals, self.__renderProps(self.parsed, ' '))

class TaskRunnerCore:
	__ordinals = ['_', 'first','second','third','fourth', 'last']
	__counts = ['_', '_', 'one','two','three','four']

	active = True
	verbose = False

	argumentLabels = []
	allowedClauses = []
	allowedOrdinals = []
	defaults = {}

	cmdLine = 0
	fileName = ''
	task = ''

	lines = {}
	data = {
		'cwd': '.', 'loops': 0, 'selection': False,
		'userpath': os.path.expanduser('~'),
		'pythonpath': sys.executable,
		'testList': ['a', 'b', 'c', 'd', 'e', 'f', 'g']
	}

	def __init__(self, taskFilePath=False):
		if taskFilePath:
			if taskFilePath.endswith('.tsl'):
				self.fileName = taskFilePath
				with io.open(taskFilePath, 'r', encoding='utf8') as taskFile:
					self.task = taskFile.read()
			elif taskFilePath.endswith('.py'):
				print('! You are trying to run a Python script using TaskRunner. If in Sublime, please change your Tools > Build System to Python !')
			else:
				print('! This is not a valid task file !')

	def __isLiteral(self, anyString):
		if not isinstance(anyString, str): return False
		return anyString.startswith('"') and anyString.endswith('"')
	
	def __isRaw(self, anyString):
		return anyString.startswith('/') and anyString.endswith('/')

	def __isReference(self, anyString):
		if isinstance(anyString, str):
			return anyString.startswith('[') and anyString.endswith(']')
		return False

	def __parseNumbers(self, item):
		if item.isdigit() or (item[1:].isdigit() and item[0] == '-'):
			return int(item) - 1
		return item

	def __normalizeLiterals(self, args):
		openQuotes = []
		closeQuotes = []

		for i, token in enumerate(args):
			if token.startswith('"'):
				if not token.endswith('"'):
					openQuotes.append(i)
			elif token.endswith('"'):
				if not token.startswith('"'):
					closeQuotes.append(i+1)

		openQuotes.reverse()
		closeQuotes.reverse()
		
		for i, openQuote in enumerate(openQuotes):
			if len(closeQuotes) >= i:
				closeQuote = closeQuotes[i]
			else:
				closeQuote = -1
				raise SyntaxError(' String needs to have closing quotation mark near:\n  %s' % (self.lines[self.cmdLine-1]))
			args[openQuote:closeQuote] = [' '.join(args[openQuote:closeQuote])]

		return args

	def __extractClauses(self, args, parsedArgs):
		upForDeletion = []

		for i, token in enumerate(args):
			if self.__isLiteral(token):
				parsed = self.parseVars(token)[1:-1]
				if parsed != token:
					parsedArgs.parsed[parsed.encode('utf8')] = token
				args[i] = parsed
				parsedArgs.literals.append(token[1:-1])
			elif token in self.allowedClauses:
				parsedArgs[token] = args[i+1]
				if token in self.allowedOrdinals:
					args[i+1] = self.__parseNumbers(args[i+1])
				upForDeletion.extend([i, i+1])
				parsedArgs.clauses.append(token)
			elif self.__isReference(token):
				args[i] = self.getData(token[1:-1])
				parsedArgs.referenced[token[1:-1]] = args[i]

		upForDeletion.reverse()

		for i in upForDeletion:
			del args[i]

		for token in self.allowedClauses:
			if token in parsedArgs:
				arg = parsedArgs[token]

				if self.__isReference(arg):
					parsedArgs[token] = self.getData(arg[1:-1])
				elif self.__isLiteral(arg):
					arg = arg[1:-1]
				else:
					parsedArgs[token] = self.__parseNumbers(str(arg))

		return (args, parsedArgs)

	def __resolveOrdinals(self, token, item):
		if token in self.allowedOrdinals:
			if item in self.__ordinals:
				if item == 'last':
					item = -1
				else:
					return self.__ordinals.index(item) - 1
			else:
				return self.__parseNumbers(item)
		return item

	def isActive(self):
		return self.active

	def isNumber(self, nr):
	    try:
	        float(nr)
	        return True
	    except ValueError:
	        return False

	def pluck(self, dict, *args):
		return [dict[arg] for arg in args]

	def parseVars(self, toParse):
		return re.sub(r'(?<!\\)\[([^]]+)\]', lambda match: str(self.getData(match.group()[1:-1])), toParse, re.I)

	def getData(self, name=False):
		if name: 
			if name in self.data:
				return self.data[name]
			else:
				return '[%s]' % name

		selection = self.data['selection']

		if selection:
			if selection in self.data:
				return self.data[selection]
			elif 'line' in self.data:
				return self.data['line']
		return False

	def setData(self, name, value=None):
		if value is None:
			value = name
			name = self.data['selection']
		self.data[name] = value

	def runLine(self, cmdLine):
		command = self.lines[cmdLine].strip()
		self.cmdLine = cmdLine + 1

		command = re.split(r'[\s\t]+', command.strip())

		if not command[0].startswith('#') and len(command):
			if command[0][0:3] == '---':
				command[0] = 'repeat'
			
			self.argumentLabels = []
			self.allowedClauses = []
			self.allowedOrdinals = []
			self.defaults = {}

			self.executeCommand(command)

		if self.isActive() and self.cmdLine < len(self.lines):
			self.runLine(self.cmdLine) 

	def addClauses(self, *clauses):
		self.allowedClauses.extend(clauses)
		return self

	def addSyntax(self, *labels):
		self.argumentLabels.append(labels)
		return self

	def addDefaults(self, options):
		self.defaults = options
		return self

	def allowOrdinals(self, *labels):
		self.allowedOrdinals.extend(labels)
		return self

	def parseArgs(self, args, debug=False):
		# set defó values
		parsedArgs = TaskRunnerArgs(args, self.defaults)

		args = self.__normalizeLiterals(args)		
		args, parsedArgs = self.__extractClauses(args, parsedArgs)

		#find registered argument patterns for correct property assignment
		matchedPattern = False
		
		for pattern in self.argumentLabels:
			match = True
			if not matchedPattern:
				pattern = list(filter(None, pattern))
				if len(pattern) == len(args):
					if len(pattern):
						for i, token in enumerate(pattern):
							if self.__isLiteral(token):
								if re.match(token[1:-1], args[i]):
									match = match and True
									if match:
										matchedPattern = pattern
								else:
									match = False	
									matchedPattern = False
							else: 
								match = match and True
								matchedPattern = pattern
					else:
						match = True
						matchedPattern = pattern
				else:
					match = False	
					matchedPattern = False

		if matchedPattern:
			for i, token in enumerate(matchedPattern):
				if not self.__isLiteral(token):
					if self.__isRaw(token):
						token = token[1:-1]
						key = str(args[i]).encode('utf8')
						if key in parsedArgs.parsed:
							args[i] = parsedArgs.parsed[key][1:-1]
					else:
						args[i] = self.__resolveOrdinals(token, args[i])

						if isinstance(args[i], int):
							parsedArgs[token] = args[i]
						elif self.__isReference(token):
							parsedArgs[token] = self.getData(args[i])
							parsedArgs.referenced[token] = args[i]
						else:
							parsedArgs.referenced[token] = parsedArgs.findRef(args[i])

					parsedArgs[token] = args[i]
				elif '|' in token:
					parsedArgs[args[i]] = True

		parsedArgs.arguments = args

		self.argumentLabels = []
		self.allowedClauses = []
		self.allowedOrdinals = []
		self.defaults = {}

		return parsedArgs

	def executeCommand(self, command):
		if hasattr(self, '_' + command[0]):
			#print('_' + command[0], command[1:])
			eval('self._' + command[0])(command[1:])
			#print('-'*50)
			#print('\n')
		else:
			print(' !', command[0], 'is no valid command !')

	def parse(self, task):
		isTask = re.findall(r'\{\n\s*([\w\W]+)\s*\n\}', task)

		if len(isTask):
			return re.split(r'\s*[\n\r]\s*|\s*and\s*', isTask[0])

		print(' ! No viable task found !')
		return False

	def run(self):
		task = self.parse(self.task)

		if task:
			self.lines = task
			self.runLine(0)
			print('')
		
		return self