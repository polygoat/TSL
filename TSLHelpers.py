import os
import re
import sys
import json
import inspect

# ------------------------------------------------------------------
# Hackaround for Python's tail recursion issue (mainly for runLine)
# ------------------------------------------------------------------

class Recurse(Exception):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

def recurse(*args, **kwargs):
    raise Recurse(*args, **kwargs)
        
def tail_recursive(f):
    def decorated(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except Recurse as r:
                args = r.args
                kwargs = r.kwargs
                continue
    return decorated

def getClassMethods(theClass, internals=True, clean=False, startswith=''):
	name = theClass.__name__
	methods = [item[0] for item in inspect.getmembers(theClass) if callable(item[1]) and len(item[0])]
	if not internals:
		methods = list(filter(lambda method: (not method.startswith('__')) and method.startswith(startswith), methods))

	if clean:
		methods = [method[1:] for method in methods]

	return methods

# -------------------------------------------------------
# TSL specific helper classes
# -------------------------------------------------------

class TSLUtils:
	@staticmethod
	def map(method, array):
		return list(map(method, array))

	@staticmethod
	def ensureList(maybeList, entry=None):
		if isinstance(maybeList, dict):
			if entry in maybeList:
				return maybeList[entry]
			else:
				maybeList[entry] = []
		else:
			maybeList = { entry: [] }

		return maybeList

	@staticmethod
	def parseVars(toParse):
		results = toParse + r''
		matches = re.findall(r'(?<!\\)\[([^]]+)\]', toParse, re.I)

		for match in matches:
			try:
				results = re.sub(r'(?<!\\)\[%s\]' % match, str(TSLData[match]), results, re.I)
			except: 
				continue

		return results

class TSLData(dict):
	__data = {}

	def __init__(self):
		TSLData.__data = { 'initialized': 1 }

	def __contains__(self, which):
		return which in TSLData.__data

	def __getitem__(self, which, default=None):
		if isinstance(which, tuple):
			default = which[1]
			which = which[0]
		else:
			if default is None:
				default = '[%s]' % which

		if len(which):
			if which in TSLData.__data:
				return TSLData.__data[which]
		else:
			selection = TSLData.__data.get('selection', False)
			if selection:
				if selection in TSLData.__data:
					return TSLData.__data[selection]
				elif 'lines' in TSLData.__data:
					return TSLData.__data['lines']

		return default

	def __setitem__(self, which, what):
		TSLData.__data[which] = what

	@staticmethod
	def reset():
		TSLData.__data = {
			'userpath':  os.path.expanduser('~'),
			'cwd':  	 '.',
			'loops':  	 0,
			'selection': False,
			'pythonpath': sys.executable
		}

class TSLCollection(list):
	separator = '\n'
	lines = []
	lineNrs = []
	results = []

	@staticmethod
	def isIt(toCheck):
		return isinstance(toCheck, TSLCollection)

	def __init__(self, elements):
		self.setTo(elements)

	def __len__(self):
		return len(self.results)

	def __str__(self):
		results = re.sub(r'\s*,\s*', ',', str(self.results))
		if len(results) > 40:
				results = results[0:40] + '...' + results[-6:-1] + ']'
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

	def filter(self, filterMethod, args=[]):
		self.lineNrs = []
		self.results = []

		def createResults(entry, id):
			result = filterMethod(entry, id, *args)
			if result:
				self.lineNrs.append(id)
				if isinstance(result, list) and len(result) == 1:
					result = result[0]
				self.results.append(entry)

		for id, element in enumerate(self, start=1):
			createResults(element, id)
		return self


class TSLQuantifiers:
	arguments = []
	collection = None

	@staticmethod
	def resolve(args, collection=TSLCollection([])):
		if args[0] in ['every', 'all']:
			if len(args) > 1:
				args = args[1]
			else:
				args = 'all'
		else:
			args = args[0]

		filtered = TSLQuantifiers._every(args, collection)
		return filtered

	@staticmethod
	def _no(item, index):
		return False

	@staticmethod
	def _none(item, index):
		return False

	@staticmethod
	def _nth(item, index, ordinal=1):
		return not (index) % ordinal

	@staticmethod
	def _all(item, index): 
		return True

	@staticmethod
	def _odd(item, index):
		return TSLQuantifiers._nth(item, index, 2)

	@staticmethod
	def _other(item, index): 	
		return TSLQuantifiers._even(item, index)

	@staticmethod
	def _even(item, index): 
		nr = TSLQuantifiers._nth(item, index, 2)
		return not TSLQuantifiers._nth(item, index, 2)

	@staticmethod
	def _every(selector='all', collection=[]):
		try:
			args = [int(selector)]
			method = TSLQuantifiers._nth
		except: 
			args = []
			if hasattr(TSLQuantifiers, '_' + selector):
				method = getattr(TSLQuantifiers, '_' + selector)

		TSLQuantifiers.collection = collection.filter(method, *args)
		#collection = [item for index, item in enumerate(collection) if method(item, index, *args)]
		return collection

class TSLSyntax(list):
	def __init__(self, syntax):
		self.extend(syntax)
		self.size = len(syntax)
		self.reset()

	def __len__(self):
		return self.match+1

	def __repr__(self):
		theList = self[:max(1,self.match+1)]
		extras = []

		if self.size > max(1, self.match+1):
			active = ['>> ' + repr(self[max(1, self.match+1)]) + ' <<']
			if self.size > max(1, self.match+1)+1:
				extras = self[max(1, self.match+1)+1:]

		else:
			active = []

		return str(theList + active + extras)

	def reset(self):
		self.match = self.size-1
		return self

class TSLArg:
	name = 'default'

	ordinals = {
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

	numbers = {
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
	}

	def __init__(self, name, datatype='any', *others):
		self.name = name
		self.value = None
		self.default = None
		self.datatype = None
		self.parsed = {}

		if len(others):
			self.datatype = [datatype] + list(others)
		elif isinstance(datatype, list):
			self.enum = datatype
			self.datatype = 'enum'
		elif datatype is ...:
			self.datatype = 'remainder'
		else:
			self.datatype = datatype

	def __contains__(self, value):
		if self.datatype == 'enum':
			return value in self.enum
		return value in self

	def __eq__(self, value):
		return self.satisfies(value)

	def __ne__(self, value):
		return not self.__eq__(value)

	def __repr__(self):
		return self.name

	def __str__(self):
		return '<TSLArg %s:%s %s>' % (self.name, self.datatype, self.parsed)

	def isString(self, value):
		return True

	def parseString(self, value):
		return value

	def isAny(self, value):
		return True

	def parseAny(self, value):
		parsers = ['reference', 'literal', 'numeric']
		for parser in parsers:
			parser = parser.capitalize()
			isType = getattr(self, 'is' + parser)(value)
			if isType:
				return getattr(self, 'parse' + parser)(value)
		return TSLUtils.parseVars(value)

	def isRaw(self, value):
		return '[' in value and ']' in value

	def parseRaw(self, value):
		return value

	def isRemainder(self, value):
		return isinstance(value, list) or isinstance(value, str)

	def parseRemainder(self, value):
		return self.parseAny(value)

	def isInt(self, nr):
	    try:
	        int(nr)
	        return True
	    except ValueError:
	        return False

	def parseInt(self, nr):
		return int(nr)

	def isFloat(self, nr):
	    try:
	        float(nr)
	        return True
	    except:
	        ...
	    return False

	def parseFloat(self, nr):
		return float(nr)

	def isOrdinal(self, value):
		return value in TSLArg.ordinals

	def parseOrdinal(self, value):
		self.parsed['ordinals'] = True
		return TSLArg.ordinals.get(value, value)
	
	def isCount(self, value):
		return value in TSLArg.numbers or self.isInt(value)

	def parseCount(self, value):
		self.parsed['counts'] = True
		return self.numbers.get(value, self.parseInt(value))

	def isNumeric(self, value):
		return self.isFloat(value) or self.isOrdinal(value) or self.isCount(value)

	def parseNumeric(self, value):
		for datatype in ['ordinal', 'count', 'int', 'float']:
			if getattr(self, 'is' + datatype.capitalize())(value):
				return getattr(self, 'parse' + datatype.capitalize())(value)
		return value

	def isLiteral(self, anyString):
		if isinstance(anyString, str): 
			return anyString.startswith('"') and anyString.endswith('"')
		return False

	def parseLiteral(self, anyString):
		self.parsed['literals'] = True
		return anyString[1:-1]

	def isReference(self, anyString):
		if isinstance(anyString, str):
			return anyString.startswith('[') and anyString.endswith(']')
		return False

	def parseReference(self, anyString):
		reference = anyString[1:-1]
		self.parsed['references'] = reference
		return TSLData[reference]

	def satisfies(self, value, datatype=None):
		if datatype is None:
			datatype = self.datatype

		if datatype in ['any','string']:
			return True
		elif datatype == 'enum':
			return value in self.enum
		elif isinstance(datatype, list):
			return any([self.satisfies(value, item) for item in datatype])

		checkMethod = 'is%s' % datatype.capitalize()
		if hasattr(self, checkMethod):
			return getattr(self, checkMethod)(value)

		return False

	def set(self, value):
		if self.datatype == 'enum':
			if value in self.enum:
				self.value = value		
			else:
				raise ValueError('Parameter "%s" must be one of: %s' % (self.name, ', '.join(self.enum)))
		else:
			if isinstance(self.datatype, list):
				datatypes = self.datatype
			else:
				datatypes = [self.datatype]

			for datatype in datatypes:
				checkMethod = 'is%s' % datatype.capitalize()
				parseMethod = 'parse%s' % datatype.capitalize()
				

				if hasattr(self, parseMethod):
					if getattr(self, checkMethod)(value):
						value = getattr(self, parseMethod)(value)
						self.value = value
						return self

		return self
		
class TSLArgs(dict):
	quantifiers = []
	hooks = {}

	command = 'unknown'

	def __getattr__(self, attr):
		return self[attr]

	def __init__(self, cmd):
		self.__argCount = 0
		self.__allowedClauses = []
		self.__allowedQuantifiers = []
		self.__requiredClauses = []
		self.__defaults = {}
		self.__patterns = []
		self.__matches = []
		self.matchedSyntax = ['']
		self.intercepted = False
		self.command = cmd
		self.references = {}
		self.quantifiers = {}
		self.ordinals = []
		self.literals = []
		self.counts = []
		self.raw = []

	def supportSyntax(self, *args):
		self.__patterns.append(TSLSyntax(args))
		return self

	def allowClauses(self, *clauses):
		self.__allowedClauses.extend(clauses)
		return self
	
	def allowQuantifiers(self, *qufs):
		self.__allowedQuantifiers.extend(qufs)
		return self

	def setDefaults(self, defaults):
		#for default, value in defaults.items():
		#	for syntax in self.__patterns:
		#		for arg in syntax:
		#			if repr(arg) == default:
		#				arg.default = value
		self.__defaults = defaults
		return self

	def requireClauses(self, *clauses):
		self.__requiredClauses.extend(clauses)
		return self

	@tail_recursive
	def matchSyntax(self, arg, hasPrevArg, index=0):
		if self.matchedSyntax:
			return

		if index < len(self.__matches):
			syntax = self.__matches[index]
		else: 
			patterns = '\n\t'.join(['  '.join(map(TSLArgs.__withDatatype, pattern)) for pattern in self.__patterns])
			raise TypeError('Wrong parameter "%s" for "%s". Allowed are:\n\t%s' % (str(arg), self.command, patterns))

		syntaxArg = repr(syntax[syntax.match])

		if arg == syntax[syntax.match]:
			if isinstance(syntax[syntax.match], TSLArg) and syntax[syntax.match].datatype == 'remainder':
				if syntax.size == 1 or hasPrevArg:
					value = syntax[syntax.match].value
				
				if value is None:	value = arg
				else:				value.insert(0, arg)

				if isinstance(value, list):
					value = ' '.join(value)
				
				syntax[syntax.match].set(value)

			else:
				syntax.match -= 1

			if not hasPrevArg:
				syntax.reset()
				self.matchedSyntax = syntax
		else:
			del self.__matches[index]
			index -= 1

		if index+1 < len(self.__matches):
			self.matchSyntax(arg, hasPrevArg, index+1)

	@tail_recursive
	def matchArg(self, args, index=0):
		self.__argCount = len(args)
	
		if self.__argCount:
			hasPrevArg = index < self.__argCount-1
			isClause = False
			arg = args[index]

			if hasPrevArg:
				prevArg = args[index+1]

			if arg in TSLArgs.quantifiers:
				quantifiers = [arg]

				isClause = True

				if hasPrevArg:
					if prevArg in TSLArgs.quantifiers:
						quantifiers = args[index+1:index-1:-1]
						del args[index+1]
						self.__argCount -= 1

				del args[index]
				index -=2
				self.__argCount -= 1
				self.quantifiers[args[index+1]] = quantifiers

				hasPrevArg = index < self.__argCount-1
				arg = args[index]
			elif hasPrevArg:
				clauses = TSLUtils.map(self.clean, self.__allowedClauses)

				if prevArg in clauses:
					clauseArg = [clauseArg for clauseArg in self.__allowedClauses if isinstance(clauseArg, TSLArg) and clauseArg.name == prevArg]
					if len(clauseArg):
						clauseArg = clauseArg[0]
						if prevArg != clauseArg:
							pattern = ', '.join(clauseArg.datatype)
							raise TypeError('Wrong datatype for clause "%s" of "%s". Allowed are: %s' % (prevArg, self.command, pattern))
						else:
							arg = clauseArg.set(arg).value

					self[prevArg] = arg
					del args[index+1]
					del args[index]
					isClause = True
					index -= 1
					self.__argCount -= 2

			if not isClause:
				self.matchSyntax(arg, hasPrevArg)

			if index < self.__argCount-1:
				args = self.matchArg(args, index+1)
			elif not self.matchedSyntax:
				patterns = '\n\t'.join([' '.join(map(TSLArgs.__withDatatype,pattern)) for pattern in self.__patterns])
				args.reverse()
				raise TypeError('Wrong syntax "%s %s". Allowed are:\n\t%s' % (self.command, ' '.join(map(TSLArgs.clean, args)), patterns))
			
			args.reverse()
		return args

	def parseArgs(self, args):
		for clauseArg in self.__allowedClauses:
			if isinstance(clauseArg, TSLArg) and clauseArg.name in self.__defaults:
				clauseArg = clauseArg.set(self.__defaults[clauseArg.name])
				self.__defaults[clauseArg.name] = clauseArg.value
				self.applyMetadata(clauseArg, clauseArg.name)
		
		self.update(self.__defaults)

		args.reverse()
		self.__matches = self.__patterns.copy()
		self.matchedSyntax = False
		args = self.matchArg(args)
		args.reverse()

		for i, arg in enumerate(args):
			if i < self.matchedSyntax.size:
				syntaxArg = self.matchedSyntax[i]

				if isinstance(syntaxArg, TSLArg):
					name = syntaxArg.name
					arg = syntaxArg.set(arg)
					self.applyMetadata(arg, name)
					self[name] = arg.value
				else:
					self[str(syntaxArg)] = True

		self.raw = args
		return self

	# get parsed info like refs, ordinals, ...
	def applyMetadata(self, arg, name):
		for key, value in arg.parsed.items():
			store = getattr(self, key)
			if isinstance(store, dict):
				if name not in store:
					store[name] = value
			elif isinstance(store, list):
				if name not in store:
					store.append(name)
			setattr(self, key, store)
		return self

	@staticmethod
	def clean(what):
		if isinstance(what, str):
			return what
		return repr(what)

	@staticmethod
	def __withDatatype(arg):
		if isinstance(arg, TSLArg):
			if arg.datatype == 'enum':
				datatype = "'" + "'/'".join(arg.enum) + "'"
			else:
				datatype = arg.datatype
			return '%s <%s>' % (arg.name, datatype)
		return arg

	def __log__(self, props, glue='\n\t'):
		return glue.join(['%s=%s' % (prop, json.dumps(value, sort_keys=True, indent=4).replace('\n','\n\t')) for prop, value in props.items()])

	def __str__(self):
		params = self.__log__(self)
		refs = self.__log__(self.references, ', ')

		propList = ''

		for key in ['references','literals','quantifiers','counts','raw']:
			props = getattr(self, key)
			if len(props):
				if isinstance(props, dict):
					propList += '\n\t%s=[%s]' % (key, self.__log__(props, ', ').replace('\n', ' '))
				elif isinstance(props, list):
					propList += '\n\t%s=%s' % (key, props)
				else:
					propList += '\n\t%s="%s"' % (key, props)

		if len(params):
			params = '\n\t' + params + '\n'

		return '<TSLArguments.{command}{params}\t\n\tsyntax="{syntax}"{props}\n/>'.format(command=self.command, params=params, syntax=' '.join(map(TSLArgs.clean, self.matchedSyntax)), props=propList)

class TSLInflector:
	__irregulars = {
			"child": "children",
			"goose": "geese",
			"man": "men",
			"woman": "women",
			"tooth": "teeth",
			"foot": "feet",
			"mouse": "mice",
			"person": "people"
		}

	@staticmethod
	def singular(word):
		if word in TSLInflector.__irregulars.values():
			rev = {v: k for k, v in TSLInflector.__irregulars.items()}
			return rev[word]

		if word.endswith('ies'):
			return word[0:-3] + 'y'
		elif word.endswith('ae'):
			return word[0:-2] + 'a'
		elif word.endswith('oes'):
			if len(word) > 4:
				return word[0:-2]
			return word[0:-1]
		elif word.endswith('ives'):
			return word[0:-3] + 'fe'
		elif word.endswith('lves'):
			return word[0:-3] + 'f'
		elif word.endswith('lves'):
			return word[0:-3] + 'f'
		elif word.endswith('ces'):
			return word[0:-3] + 'x'
		elif word.endswith('s'):
			return word[0:-1]

		return word

	@staticmethod
	def plural(word):
		if word in TSLInflector.__irregulars:
			return TSLInflector.__irregulars[word]
		elif word.endswith('as'):
			return word + 'ses'
		elif word[-2:] in ['ss','sh','ch'] or word.endswith('o') or word[-1] in ['s','x','z']:
			return word + 'es'
		elif word.endswith('f'):
			return word[0:-1] + 'ves'
		elif word.endswith('fe'):
			return word[0:-2] + 'ves'
		elif word.endswith('is'):
			return word[0:-2] + 'es'
		elif word.endswith('on'):
			return word[0:-2] + 'a'
		elif word.endswith('y') and word[-2] not in ['a','e','o','u']:
			return word[0:-1] + 'ies' 

		return word + 's'

TSLArgs.quantifiers = [Q[1:] for Q in dir(TSLQuantifiers) if Q[0] == '_' and Q[1] != '_']
TSLData = TSLData()


# -------------------------------------------------------
# Debugging crap
# -------------------------------------------------------
#args = ['every', 'other']
#args = ['every', 'even']
#args = ['every', 3]
#args = ['odd']
#args = ['all']
#args = ['none']

#C = TSLCollection(['a', 'b', 'c', 'd', 'e', 'f'])
#Q = TSLQuantifiers(C)

#command = args[0]

#if command in methods:
#	args = Q.resolve(args)
# 	print('args', args)
#
#else:
#	print('method doesn\'t exist.')

#tester = TSLArgs('select')
#tester.supportSyntax(TSLArg('what', ['lines', 'folders', 'files']))
#tester.supportSyntax(TSLArg('which', 'ordinal'))
#tester.supportSyntax('something', TSLArg('etc', ...))
#tester.supportSyntax(TSLArg('count', 'count'))
#tester.supportSyntax(TSLArg('one', 'reference'), 'by', TSLArg('two', 'reference'))
#tester.supportSyntax(TSLArg('nr', 'count'), 'from', TSLArg('two', 'reference'))
#tester.allowClauses('as', TSLArg('to', 'float', 'reference'))
#tester.allowClauses(TSLArg('of', 'reference'))
#tester.setDefaults({ 'of':'[hui]', 'bloo': 'woo' })
#args = ['something',  'strange', 'is', 'happening...']

#args = ['[hui]', 'by', '[y]']

#TSLData['hui'] = 'pfui'
#print(tester.parseArgs(args))

ary = ['find', 'every', 'other']
#ary = ['every', 'other']
#ary = ['all']

ary.reverse()
argCount = len(ary)

i = 0
prevArg = ary[i]
if argCount > i+1:
	prevPrevArg = ary[i+1]
else:
	prevPrevArg = False

#while prevArg in TSLArgs.quantifiers:
#	hasPrevArg = i < argCount-1
#
#	if hasPrevArg:
#		prevArg = ary[i+1]
#	else:
#		prevArg = False
#	i += 1

#quantifiers = ary[:i][::-1]

#print(prevPrevArg, prevArg)