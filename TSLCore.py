import io
import os
import re
import hashlib
import sys
from .glob2 import glob
from TSL.TSLHelpers import *

class TSLCollection(list):
	separator = '\n'
	lines = []
	lineNrs = []
	results = []

	def __init__(self, elements):
		self.setTo(elements)

	def __len__(self):
		return len(self.results)

	def __str__(self):
		results = re.sub(r'\s*,\s*', ',', str(self.results))
		if len(results) > 10:
				results = results[0:10] + '...' + results[-6:-1] + ']'
		return '<TSLColl(%d) %s>' % (len(self.results), results)

	def applyResults(self):
		return TSLCollection(self.results)

	def getFiltered(self, which):
		return [element for id, element in enumerate(which, start=1) if id in self.lineNrs]

	def setTo(self, elements):
		self.clear()
		self.lines.clear()
		self.lineNrs.clear()
		self.results.clear()

		for i, element in enumerate(elements, start=1):
			self.append(element)
			self.lines.append(element)
			self.results.append(element)
			self.lineNrs.append(i)
		return self

	def join(self):
		return self.separator.join(self)

	def filter(self, filterMethod):
		self.lineNrs = []
		self.results = []

		def createResults(entry, id):
			result = filterMethod(entry, id)
			if result:
				self.lineNrs.append(id)
				if isinstance(result, list) and len(result) == 1:
					result = result[0]
				self.results.append(result)

		for id, element in enumerate(self, start=1):
			createResults(element, id)
			
		return self

class TSLArgs(dict):
	hooks = {}

	def __init__(self, args, defaults={}, debug=''):
		self.arguments = []
		self.parsed = {}
		self.referenced = {}
		self.toReference = {}
		self.literals = []
		self.clauses = []
		self.counted = []
		self.method = debug
		self.intercepted = False

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
				v = v[0:20] + '...' + v[-6:]

			propList.append('%s=%s' % (k, v))

		return delimiter.join(propList)

	def __str__(self):
		return '<TSLArguments.%s\n\t%s\n\tsyntax="%s"\n\treferenced[%s]\n\tliterals%s\n\tparsed[%s]\n\tcounted[%s]\n/>' % (self.method, self.__renderProps(self, '\n\t'), ' '.join(self.get('matchedPattern', [])), self.__renderProps(self.referenced, ' '), self.literals, self.__renderProps(self.parsed, ' '), ','.join(self.counted))

class TSLCore:
	__logger = {
		'log': print
	}

	__ordinals = {
		'1st': 		1,		'first': 	1,
		'2nd': 		2,		'second': 	2,
		'3rd': 		3,		'third': 	3,
		'4th': 		4,		'fourth': 	4,
		'5th': 		5,		'fifth': 	5,
		'6th': 		6,		'sixth': 	6,
		'7th': 		7,		'seventh': 	7,
		'8th': 		8,		'eigth': 	8,
		'9th': 		9,		'nineth': 	9,
		'last': 	-1,
		'butlast': -2
	}

	__numbers = {
		'none': 0, 		'zero': 	0,
		'one': 1, 		'single': 	1,
		'two': 2,
		'three': 3,
		'four': 4,
		'five': 5,
		'six': 6,
		'seven': 7,
		'eight': 8,
		'nine': 9,
		'ten': 10,
		'eleven': 11,
		'twelve': 12, 	'dozen': 12,
		'all': -1
	}

	__plurals = {}

	active = True
	verbose = False

	argumentLabels = []
	allowedClauses = []
	allowedOrdinals = []
	allowedCounts = []

	defaults = {}
	plugins = {}
	parsers = {}
	hooks = {}

	cmdLine = 0
	fileName = ''
	task = ''

	lines = {}
	data = {
		'userpath': os.path.expanduser('~'),
	}

	def __init__(self, taskFilePath=False):
		self.data['cwd'] = '.'
		self.data['loops'] = 0
		self.data['selection'] = False
		self.data['pythonpath'] = sys.executable
		self.data['testList'] = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

		if taskFilePath:
			if taskFilePath.endswith('.tsl'):
				self.fileName = taskFilePath
				with io.open(taskFilePath, 'r', encoding='utf8') as taskFile:
					self.task = taskFile.read()
			elif taskFilePath.endswith('.py'):
				self.log('! You are trying to run a Python script using TSL. Please change your Tools > Build System to Python !')
			else:
				self.log('! This is not a valid task file !')

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
		if isinstance(item, str):
			if item.isdigit() or (item[1:].isdigit() and item[0] == '-'):
				return int(item) - 1
			else:
				return self.__resolveNumber(item)
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
		lastToken = False

		for i, token in enumerate(args):
			if token in self.allowedOrdinals:
				args[i+1] = self.__resolveOrdinals(token, args[i+1], parsedArgs)
			if token in self.allowedCounts:
				args[i+1] = self.__resolveCounts(token, args[i+1], parsedArgs)
			
			if self.__isLiteral(token):
				parsed = self.parseVars(token)[1:-1]
				if parsed != token:
					parsedArgs.parsed[parsed.encode('utf8')] = token
				args[i] = parsed
				parsedArgs.literals.append(token[1:-1])
			elif token in self.allowedClauses:
				parsedArgs[token] = args[i+1]
				upForDeletion.extend([i, i+1])
				parsedArgs.clauses.append(token)
				lastToken = token
			elif self.__isReference(token):
				args[i] = self.getData(token[1:-1])
				if lastToken:
					parsedArgs.referenced[lastToken] = token[1:-1]
				else:
					parsedArgs.toReference[i] = token[1:-1]
			

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
					parsedArgs[token] = self.__parseNumbers(arg)

		return (args, parsedArgs)

	def __resolveOrdinals(self, token, ordinal, parsedArgs):
		if token in self.allowedOrdinals:
			if ordinal in self.__ordinals.keys():
				ordinal = self.__ordinals[ordinal]
				if ordinal > 0:
					ordinal -= 1
		return ordinal

	def __resolveNumber(self, nr):
		if nr in self.__numbers.keys():
			nr = self.__numbers[nr]
			if nr > 0:
				return nr-1
		return nr

	def __resolveCounts(self, token, nr, parsedArgs):
		if token in self.allowedCounts:
			if isinstance(nr, str):
				if nr in self.__numbers.keys():
					nr = self.__numbers[nr]
					parsedArgs.counted.append(token)
		return nr

	def __resolveCount(self, nr, collection):
		if nr in self.__numbers.keys():
			nr = self.__numbers[nr]
			if nr > 0:
				return nr
			elif nr == -1:
				return len(collection)
			return nr

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

	def isNumber(self, nr):
	    try:
	        float(nr)
	        return True
	    except ValueError:
	        return False

	def pluck(self, dict, *args):
		return [dict[arg] for arg in args]

	def toPlural(self, word):
		plural = self.__plurals.get(word)
		if not plural:
			plural = Inflector.plural(word)
			self.__plurals[word] = plural
		return plural

	def fromPlural(self, word):
		if word in self.__plurals:
			__singulars = {value: key for key, value in self.__plurals.items()}
			singular = __singulars[word]
		else:
			singular = Inflector.singular(word)
			self.__plurals[singular] = word
		return singular

	def parseVars(self, toParse):
		results = toParse + r''
		matches = re.findall(r'(?<!\\)\[([^]]+)\]', toParse, re.I)

		for match in matches:
			try:
				results = re.sub(r'(?<!\\)\[%s\]' % match, str(self.getData(match)), results, re.I)
			except: 
				continue

		return results

	def getData(self, name=False, fallback='[%s]'):
		if name and isinstance(name, str): 
			if name in self.data:
				return self.data[name]
			elif isinstance(fallback, str):
				return fallback % name
			else:
				return fallback

		selection = self.data['selection']

		if selection:
			if selection in self.data:
				return self.data[selection]
			elif 'lines' in self.data:
				return self.data['lines']
		return False

	def setData(self, name, value=None):
		if value is None:
			value = name
			name = self.data['selection']
		self.data[name] = value

	def resolveAsClause(self, varName, value):
		self.setData(varName, value)
		#self.setData('selection', varName)
		if self.looping:
			if varName != 'selection':
				plural = self.toPlural(varName)
				if plural != varName:
					collection = self.getData(plural, fallback=False)

					if collection:
						collection.append(value)
					else:
						collection = [value]
					self.setData(plural, collection)

	@tail_recursive
	def runLine(self, cmdLine):
		command = self.lines[cmdLine].strip()
		self.cmdLine = cmdLine + 1

		command = re.split(r'[\s\t]+', command)

		if not command[0].startswith('#') and len(command):
			if command[0][0:3] == '---':
				command[0] = 'repeat'
			
			self.argumentLabels = []
			self.allowedClauses = []
			self.allowedOrdinals = []
			self.allowedCounts = []
			self.defaults = {}

			self.executeCommand(command)

		if self.isActive() and self.cmdLine < len(self.lines):
			recurse(self, self.cmdLine) 

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

	def allowCounts(self, *labels):
		self.allowedCounts.extend(labels)

	def parseArgs(self, args, debug=False):
		for arg, token in self.defaults.items():
			if self.__isReference(token):
				self.defaults[arg] = self.getData(token[1:-1])

		# set default values first
		parsedArgs = TSLArgs(args, self.defaults, debug)

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
								if isinstance(args[i], str) and re.match(token[1:-1], args[i]):
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
						args[i] = self.__resolveOrdinals(token, args[i], parsedArgs)
						args[i] = self.__resolveCounts(token, args[i], parsedArgs)
						
						if isinstance(args[i], int):
							parsedArgs[token] = args[i]
						elif self.__isReference(token):
							parsedArgs[token] = self.getData(args[i])
							parsedArgs.referenced[token] = args[i]

					parsedArgs[token] = args[i]
				elif '|' in token:
					parsedArgs[args[i]] = True

		parsedArgs.arguments = args
		parsedArgs.matchedPattern = matchedPattern or []

		if len(parsedArgs.toReference):
			for i, ref in parsedArgs.toReference.items():
				parsedArgs.referenced[matchedPattern[i]] = ref

		self.argumentLabels = []
		self.allowedClauses = []
		self.allowedOrdinals = []
		self.allowedCounts = []
		self.defaults = {}

		if parsedArgs.method in TSLArgs.hooks.keys():
			parsedArgs.intercepted = True
			TSLArgs.hooks[parsedArgs.method](parsedArgs)

		return parsedArgs

	def executeCommand(self, command):
		if hasattr(self, '_' + command[0]):
				eval('self._' + command[0])(command[1:])
		elif hasattr(self.expressions, '_' + command[0]):
			self.log('Expression found!', command[0], command[1:])
		elif command[0] in self.plugins:
			self.plugins[command[0]](command[1:])
		else:
			self.log(' !', command[0], 'is no valid command !')

	def parse(self, task):
		isTask = re.findall(r'\{\n\s*([\w\W]+)\s*\n\}', task)

		if len(isTask):
			return re.split(r'\s*[\n\r]\s*', isTask[0])

		self.log(' ! No viable task found !')
		return False

	def run(self):
		task = self.parse(self.task)

		if task:
			self.lines = task
			self.runLine(0)
			self.log('')
		
		return self