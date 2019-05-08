#pip install glob3
import io
import os
import re
import sys
import json
import math
import subprocess
from .glob2 import glob
from TSL.TSLCore import TSLCore, TSLCollection

# class TSLExpressions:
# 	def _no(self, collection):
# 		return []

# 	def _number(self, collection, nr):
# 		return collection[nr]

# 	def _all(self, collection): 
# 		return collection

# 	def _odd(self, collection):
# 		return [entry for i, entry in enumerate(collection) if (i+1) % 2]

# 	def _other(self, collection): 	
# 		return self._even(collection)

# 	def _even(self, collection): 	
# 		return self._every(collection, 2)

# 	def _every(self, collection, ordinal=1):
# 		args = [ordinal]
# 		return [entry for i, entry in enumerate(collection) if not (i+1) % ordinal]

# 	def _entries(self, collection, nr):
# 		return collection[0:nr]

class TSLEngine(TSLCore):
	currentFile = ''

	scopes = []
	counters = []
	collections = []
	selections = []
	states = []
	looping = False
	#expressions = TSLExpressions()

	templates = {
		'all': 			r'.*',
		'timecodes': 	r'(?P<hours>\d\d):(?P<minutes>\d\d)(?::(?P<seconds>\d\d)(?:\.(?P<milliseconds>\d\d\d)))?',
		'extension': 	r'\.([^.]+)$',
		'filename': 	r'(^|[\\/]+)([^\\/]+)$',
	}

	def __renderTimecode(self, timeCode, delimiter=','):
		return str(timeCode).replace('.',delimiter)

	def _log(self, args):
		options = self.addSyntax('what').parseArgs(args, 'log')
		
		what = options['what']
		whatReference = options.referenced.get('what', False)

		if isinstance(what, dict):
			self.log(' %s:' % options.referenced.get('what', 'what'))
			self.log(what)
			self.log('\n')
		elif whatReference:
			if len(whatReference):
				try:
					self.log(' %s: %s' % (whatReference, json.dumps(what, indent=4, sort_keys=True)))
				except UnicodeEncodeError:
					self.log(' ! %s could not be encoded for logging !' % whatReference) 
				except:
					self.log(' ' + whatReference + ': ', False)
					self.log(what)
			else:
				self.log(' ', False)
				self.log(what)
		elif len(what): 
			self.log(' ', False)
			self.log(what)
		else:
			self.log('')

	# clauses
	def _in(self, args):
		options = self.addSyntax('filePath').parseArgs(args, 'in')
		if options.intercepted: return False
		
		filePath = options['filePath']
		self.currentFile = filePath

		self.setData('filepath', filePath)
		self.setData('filename', os.path.basename(filePath))

		if not '.' in filePath:
			self.setData('cwd', filePath)
			if not os.path.isdir(filePath):
				try:		
					os.mkdir(filePath)
					os.chdir(filePath)
				except:		
					self.log(" ! Couldn't create directory %s !" % filePath)
			return

		extension = os.path.splitext(filePath)[1]

		if os.path.exists(filePath):
			try:
				self.data['file'] = io.open(filePath, 'r+', encoding='utf8')
				self.data['filecontent'] = self.data['file'].read()
				
				if extension in self.parsers:
					self.data['filecontent'] = self.parsers[extension].parse(self.data['filecontent'])
			except:
				self.log(' ! "%s" could not be opened !' % filePath)
		else:
			fileDir = os.path.dirname(filePath)
			dirName = os.path.dirname(fileDir).strip()

			if not len(dirName):
				dirName = fileDir
			
			if len(dirName):
				if not os.path.exists(dirName):
					try: 	
						os.makedirs(dirName, exist_ok=True)
						os.chdir(dirName)
					except: 
						self.log(' ! Could not create directory tree %s !' % (dirName))

			self.data['file'] = io.open(filePath, 'w', encoding='utf8')
			self.data['filecontent'] = ''
			self.data['filelen'] = 0

		try:
			if len(self.data['filecontent']):
				self.data['lines'] = TSLCollection(re.split(r'[\n\r]', self.data['filecontent']))
			else:
				self.data['lines'] = []

			if len(self.data['lines']) == 1 and not len(self.data['lines'][0]):
				self.data['lines'] = []
				self.data['filelen'] = 0
			else:
				self.data['filelen'] = len(self.data['lines'])

		except:
			self.data['lines'] = []
			self.data['filelen'] = 0

		if len(self.data['lines']):
			self.setData('collection', self.data['lines'])

		if self.verbose: self.log(' %s line(s) read.' % len(self.data['lines']))

	# modules
	def _run(self, args):
		self.addSyntax('script')
		options = self.parseArgs(args, 'run')

		with open(options['script'], 'r', encoding='utf8') as scriptFile:
			script = scriptFile.read()
			lines = self.parse(script)
			del self.lines[self.cmdLine-1]
			self.lines[self.cmdLine-1:self.cmdLine-1] = lines
			self.cmdLine -= 1

	# file operations
	def _empty(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args, 'empty')['what']

		if what:
			io.open(what, 'w', encoding='utf8')
			if self.verbose: self.log(' %s emptied out.' % what)
		else:
			self.setData('file', io.open(self.getData('filepath'), 'w', encoding='utf8'))
			self.setData('filelen', 0)
			if self.verbose: self.log(' %s emptied out.' % self.getData('filepath'))

	def _save(self, args):
		self.addSyntax('"as"', 'target')
		self.addDefaults({ 'target': self.getData('filepath') })
		target = self.parseArgs(args, 'save')['target']

		if not 'line' in self.data:
			self.setData('line', self.getData())

		self._empty([target])
		self._add(['[line]', 'to', target])

		if self.verbose: 
			self.log(' Saved %s as "%s".' % (self.getData('selection'), target))

	def _write(self, args):
		options = self.addSyntax('what').addDefaults({ 'what': '[found]' }).parseArgs(args, 'write')
		what = options['what']
		ref = options.referenced.get('what', 'what')
		if ref: 
			return self._add(['[%s]' % ref])
		return self._add([what])

	def _add(self, args):
		self.addSyntax('what', '"to"', 'to')
		self.addSyntax('what')
		options = self.parseArgs(args, 'add')
		
		if options['what'] == 'found':
			content = [found[1] for found in self.getData(options['what'])]
		else:
			content = options['what']
		
		if isinstance(content, list):
			try:
				content = '\n'.join(content)
			except: pass

		if 'to' in options:
			with io.open(options['to'], 'a', encoding='utf8') as target:
				filePath = self.getData('filepath')
				extension = os.path.splitext(filePath)[1]
				
				if extension in self.parsers:
					target.close()
					self.parsers[extension].write(options['to'], content)
				else:
					target.write('%s\n' % content)
					target.close()
		else:
			try:
				if self.getData('filelen'):
					self.data['file'].write('\n%s' % content)
				else:
					self.data['file'].write('%s' % content)

				self.data['filelen'] += len(content)

				if self.verbose:
					self.log(' %s saved in "%s". ' % (self.getData('selection'), self.getData('filename')))
			except: 
				self.log(' ! Could not write', self.getData('selection'), '!')
				pass

	def _bash(self, args):
		options = self.addClauses('as').addDefaults({'as':'selection'}).parseArgs(args, 'bash')

		self.resolveAsClause(options['as'], subprocess.check_output(options.arguments))

	# memory
	def _be(self, args):
		prop = self.addSyntax('property').parseArgs(args, 'be')['property']
		setattr(self, prop, True)

	def _calculate(self, args):
		self.addClauses('as')
		self.addDefaults({'as':'result'})
		options = self.parseArgs(args, 'calculate')
		result = eval(' '.join(options.arguments))
		self.resolveAsClause(options['as'], result)

	def _remember(self, args):
		self.addSyntax('what')
		self.addClauses('as')
		options = self.parseArgs(args, 'remember')	

		if not options['as']:
			options['as'] = options.referenced.get('what', 'selection')

		self.resolveAsClause(options['as'], options['what'])

	# traversal
	def _find(self, args):
		self.addSyntax('"all"', 'what')
		self.addDefaults({'in': '[collection]'})
		self.addClauses('in')

		options = self.parseArgs(args, 'find')
		stringOrRegEx = self.parseVars(options['what'])

		if stringOrRegEx in self.templates:
			stringOrRegEx = self.templates[stringOrRegEx]

		query = '%s' % stringOrRegEx

		if not isinstance(options['in'], list):
			options['in'] = [options['in']]

		isString = options['what'] in options.literals
		
		if not isString:
			stringOrRegEx = r'' + str(stringOrRegEx)

		def checkMatch(line, lineNr):
			matches = []
			group = False

			if isString:
				if stringOrRegEx in line:
					matches = [stringOrRegEx]
			else:	
				matches = re.findall(stringOrRegEx, line, re.I)
				group = re.match(stringOrRegEx, line, re.I)

			if len(matches):
				return matches
			if group:
				return group.groupdict()
			return False

		self.data['collection'].filter(checkMatch)

		if self.verbose: self.log(' found %s element(s) matching %s' % (len(self.data['collection']), query))

	def _select(self, args):
		self.addSyntax('"words"')
		self.addSyntax('which')
		self.addSyntax('')
		self.addClauses('from','to','after','until','of','as')
		self.allowOrdinals('from','to','until','which')
		self.allowCounts('which')
		self.addDefaults({'from':0, 'to':None, 'until':None, 'of': '[collection]'})
		options = self.parseArgs(args, 'select')

		if options['until']:
			options['to'] = options['until']

		of = options.referenced.get('of', options['of'])

		if len(of) == 1:
			of = of[0]

		if not 'as' in options and of:
			options['as'] = of

		if 'which' in options:
			if 'which' in options.counted:
				options['to'] = options['from'] + options['which'] - 1
			else:
				options['from'] = options['which']
				options['to'] = options['which']

		if 'words' in options:
			self.setData(re.split(r'\b', self.getData(of)))
		else:
			if 'after' in options:
				options['from'] = options['after']		

			if 'from' in options:
				if isinstance(options['from'], str):
					match = re.search(options['from'], self.getData(), re.I)
					matchLen = len(options['from'])
					
					if match: 	options['from'] = match.span()[0]
					else: 		options['from'] = 0

					if 'after' in options:
						options['from'] += matchLen - 1

			if 'to' in options:	
				if isinstance(options['to'], str) and not options['to'] is None:
					match = re.search(options['to'], self.getData(), re.I)

					if match: 	options['to'] = match.span()[0]
					else: 		options['to'] = None
				elif isinstance(options['to'], int):
					options['to'] += 1

			if options['to'] > len(self.getData(of)):
				options['to'] = None

			try:
				self.resolveAsClause(options['as'], self.getData(of)[options['from']:options['to']])
			except: 
				if options['from'] == options['to']:
					self.log(' ! %s has no index %s ! ' % (of, options['from']))
				else:
					self.log(' ! %s has no range %s to %s ! ' % (of, options['from'], options['to']))

	def _take(self, args):
		self.addSyntax('"lines|files|folders|results"')
		self.addDefaults({'as':'collection', 'in': self.getData('cwd')})
		self.addClauses('as', 'in')		

		options = self.parseArgs(args, 'take')
		varName = options['as']

		if 'lines' in options:		
			collection = self.data['collection']
			collection.setTo(collection.getFiltered(collection.lines))
			self.setData(varName, collection)

		elif 'files' in options:
			if '.' in os.path.split(options['in'])[-1]:
				path = options['in']
			else:
				path = os.path.join(options['in'],'*.*')

			#self.setData(varName, glob(path, recursive=True))
			self.resolveAsClause(varName, glob(path))
		elif 'folders' in options:
			foldersAndFiles = glob(os.path.join(options['in'], '*'), recursive=True)
			filesOnly = glob(os.path.join(options['in'], '*.*'), recursive=True)
			foldersOnly = list(set(foldersAndFiles) - set(filesOnly))

			self.setData(varName, foldersOnly)
		elif 'results' in options:
			self.setData(varName, self.getData('collection').applyResults())

		if self.getData(varName) and len(self.getData(varName)) == 1:
			self.setData(varName, self.getData(varName)[0])

	# manipulation
	def _extract(self, args):
		self.addSyntax('"timecode|duration"')
		self.addClauses('from', 'as')
		self.addDefaults({'as':'timecode'})
		options = self.parseArgs(args, 'extract')

		while len(options['from']) < 8:
			options['from'] += ':00'

		if len(options['from']) < 11:
			options['from'] += ',000'

		#if 'timecode' in options:
		#	timecode = self.__parseTimecode(options['from'])
		
		self.resolveAsClause(options['as'], timecode)

	def _change(self, args):
		self.addSyntax('what','"to"','/formula/')
		options = self.parseArgs(args, 'change')

		if isinstance(options['what'], list):
			for i, item in enumerate(options['what']):
				varName = options.referenced.get('what', 'what')
				self.data['i'] = i
				self.data['j'] = i + 1
				self.data['__' + varName] = item
				formula = self.parseVars(options['formula'].replace('[' + varName + ']', '[__' + varName + ']'))
				del self.data['__' + varName]
				self.data[varName][i] = formula
		else:
			rendered = self.parseVars(options['formula'])
			self.setData(options.referenced.get('what', 'what'), rendered)

	def _replace(self, args):
		self.addSyntax('what', '"by"', 'by')
		self.addDefaults({'in':'[collection]'})
		self.addClauses('in')
		options = self.parseArgs(args, 'replace')

		data = options['in']
		_in = options.referenced.get(data, data)

		if not _in:
			_in = data
			data = self.getData(data)
			options['in'] = data

		if isinstance(data, list):
			for i, entry in enumerate(data):
				if options['what'] in options.literals:
					data[i] = entry.replace(options['what'], options['by'])
				else:
					data[i] = re.sub(r'' + options['what'], r'' + options['by'], entry, re.I)
			self.setData(_in, data)
		else:
			if options['what'] in options.literals:
				self.setData(_in, data.replace(options['what'], options['by']))
			else:
				self.setData(_in, re.sub(options['what'], options['by'], data, re.I))

	def _split(self, args):
		self.addSyntax('what', '"by"', 'delimiter')
		self.addSyntax('"by"', 'delimiter')
		self.addSyntax('what')
		self.addDefaults({ 'what': self.getData() })
		self.addClauses('as')

		options = self.parseArgs(args, 'split')

		__byTerms = {
			"paren": r'[()]',
			"bracket": r'[{[]}]',
			"comma": ",",
			"semicolon": ";",
			"hyphen": r'\-',
			"underscore": "_",
			"period": r'\.',
			"space": r'\s+',
			"dot": r'\.',
			"tab": r'\t',
			"line": r'\n'
		}

		if not 'as' in options:
			options['as'] = options.referenced.get('what', 'collection')

		if not 'delimiter' in options.keys():
			if self.currentFile.endswith('.tsv'):
				options['delimiter'] = r'\t'
			elif self.currentFile.endswith('.csv'):
				options['delimiter'] = r','
			else:
				options['delimiter'] = r';|,|' + re.escape(os.sep)
		elif __byTerms.get(options['delimiter']):
			options['delimiter'] = __byTerms.get(options['delimiter'])
		elif __byTerms.get(options['delimiter'][:-1]):
			options['delimiter'] = __byTerms.get(options['delimiter'][:-1])

		if isinstance(options['what'], bytes):
			options['what'] = str(options['what'], 'utf8')

		self.resolveAsClause(options['as'], re.split(options['delimiter'], options['what']))

	def _count(self, args):
		self.addSyntax('"files|folders"')
		self.addSyntax('what')
		self.addClauses('as', 'in')
		self.addDefaults({'in':self.getData('cwd')})
		options = self.parseArgs(args, 'count')

		if 'files' in options:
			self.resolveAsClause(options['as'], len(glob(os.path.join(options['in'], '*.*'), recursive=True)))
		elif 'folders' in options:
			foldersAndFiles = len(glob(os.path.join(options['in'], '*'), recursive=True))
			filesOnly = len(glob(os.path.join(options['in'], '*.*'), recursive=True))
			self.resolveAsClause(options['as'], foldersAndFiles - filesOnly)
		elif 'what' in options:
			self.resolveAsClause(options['as'], len(options['what']))

	def _combine(self, args):
		self.addSyntax('x', '"with"', 'y')
		self.addClauses('as')
		self.addDefaults({'as':'selection'})
		options = self.parseArgs(args, 'combine')

		self.resolveAsClause(options['as'], options['x'] + options['y'])

	def _unique(self, args):
		self.addSyntax('what')
		self.addDefaults({'what':'[collection]'})
		options = self.parseArgs(args, 'unique')

		noDupes = []
		if isinstance(options['what'], str):
			noDupes = [options['what']]
		else:
			[noDupes.append(i) for i in options['what'] if not noDupes.count(i)]

		if len(noDupes) == 1:
			noDupes = noDupes[0]
	
		self.setData(options.referenced.get('what', 'what'), noDupes)

	def _sort(self, args):
		self.addSyntax('what')
		self.addDefaults({'what':False})
		self.addClauses('by')
		options = self.parseArgs(args, 'sort')
		what = options['what']

		if what == 'lines':
			self.getData('collection').sort()
		elif what:
			if 'by' in options:
				items = what + []
				what.sort(key=lambda item: options['by'][items.index(item)])
			else:
				what.sort()

	def _reverse(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args, 'reverse')['what']
		if what == 'lines':
			self.getData('collection').reverse()
		return what.reverse()

	def _remove(self, args):
		self.addSyntax('what')
		self.addSyntax('"empty"', '"lines|results|folders|files"')
		what = self.parseArgs(args, 'remove')['what']

		forRemoval = self.getData('collection').lineNrs.copy()

		if what == 'lines':
			def checkKeeping(entry, id):
				if id not in forRemoval:
					return entry
				return False

			collection = self.getData('collection').filter(checkKeeping).applyResults()
			self.setData('collection', collection)
		elif what == 'results':
			###
			pass
		elif what == 'folders':
			###
			pass
		elif what == 'files':
			###
			pass

	#control flow
	def _for(self, args):
		options = self.addSyntax('"every"', 'collection').parseArgs(args, 'for')
		varName = options['collection']

		if 'collection' in options.referenced:
			varName = options.referenced.get('collection')
		else:
			varName = varName[1:-1]

		collection = self.getData(self.toPlural(varName))

		if len(collection):
			if not isinstance(collection, list):
				collection = [collection]

			self.scopes.append(self.cmdLine + 1)
			self.collections.append(collection)
			self.selections.append(varName)
			self.counters.append(0)
			self.states.append(True)
			self.looping = True

			collection = self.collections[-1]

			self.data['loops'] = len(collection)
			self.data['i'] = 0
			self.data['j'] = 1
			self.data['collection'] = collection
			self.data['selection'] = varName

			self.setData(varName, self.data['collection'][0])
		else:
			if self.verbose: self.log('', varName, 'empty, for loop not iterating!')

			self.looping = False

			while self.cmdLine < len(self.lines) and self.lines[self.cmdLine] != '---':
				self.cmdLine += 1

	def _repeat(self, args=False):
		self.parseArgs(args, 'repeat')
		if len(self.scopes):

			if not self.states[-1]:
				self.states[-1] = True
				return False

			self.counters[-1] += 1
			self.data['i'] = self.counters[-1]
			self.data['j'] = self.data['i'] + 1

			if self.counters[-1] >= len(self.collections[-1]):
				self.setData(self.selections[-1], self.collections[-1])
				self.scopes.pop()
				self.counters.pop()
				self.selections.pop()
				self.collections.pop()
				self.states.pop()

				if len(self.collections):
					self.setData('collection', self.collections[-1])
					self.setData('selection', self.selections[-1])
					self.setData('i', self.counters[-1])
					self.setData('j', self.counters[-1] + 1)
				else:
					del self.data[self.data['selection']]
					self.looping = False
			else:		
				self.cmdLine = self.scopes[-1] - 1
				self.setData(self.data['selection'], self.data['collection'][self.counters[-1]])
		else:
			self.looping = False
			self.cmdLine += 1
	