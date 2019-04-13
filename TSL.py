#pip install timecode glob pprint inflect
import io
import os
import re
import sys
import json
import math
import subprocess
from glob import glob
from pprint import pprint
from TSLCore import TaskRunnerCore

class TaskRunnerExpressions:
	def _no(self, collection):
		return []

	def _number(self, collection, nr):
		return collection[nr]

	def _all(self, collection): 
		return collection

	def _odd(self, collection):
		return [entry for i, entry in enumerate(collection) if (i+1) % 2]

	def _other(self, collection): 	
		return self._even(collection)

	def _even(self, collection): 	
		return self._every(collection, 2)

	def _every(self, collection, ordinal=1):
		args = [ordinal]
		return [entry for i, entry in enumerate(collection) if not (i+1) % ordinal]

	def _entries(self, collection, nr):
		return collection[0:nr]

class TaskRunner(TaskRunnerCore):
	scopes = []
	counters = []
	collections = []
	selections = []
	states = []
	expressions = TaskRunnerExpressions()

	templates = {
		'all': 			r'.*',
		'timecodes': 	r'(?P<hours>\d\d):(?P<minutes>\d\d)(?::(?P<seconds>\d\d)(?:\.(?P<milliseconds>\d\d\d)))?',
		'extension': 	r'\.([^.]+)$',
		'filename': 	r'(^|[\\/]+)([^\\/]+)$',
	}

	def __renderTimecode(self, timeCode, delimiter=','):
		return str(timeCode).replace('.',delimiter)

	def _log(self, args):
		options = self.addSyntax('what').parseArgs(args, '_log')
		what = options['what']
		whatReference = options.findRef(what)

		if isinstance(what, dict):
			print(' %s:' % options.referenced['what'])
			pprint(what)
			print('\n')
		elif whatReference:
			if len(whatReference):
				try:
					print(' %s: %s' % (whatReference, json.dumps(what, indent=4, sort_keys=True)))
				except UnicodeEncodeError:
					print(' ! %s could not be encoded for logging !' % whatReference) 
			else:
				print('', what)
		elif len(what): 
			try:
				print('', what)
			except:
				print(' ! {%s} could not be encoded for logging !' % self.lines[self.cmdLine-1]) 
		else:
			print('')

	# clauses
	def _in(self, args):
		filePath = self.addSyntax('filePath').parseArgs(args, '_in')['filePath']

		self.setData('filepath', filePath)
		self.setData('filename', os.path.basename(filePath))

		if not '.' in filePath:
			self.setData('cwd', filePath)
			if not os.path.isdir(filePath):
				try:		os.mkdir(filePath)
				except:		print(" ! Couldn't create directory %s !" % filePath)
			return

		if os.path.exists(filePath):
			try:
				self.data['file'] = io.open(filePath, 'r+', encoding='utf8')
				extension = os.path.splitext(filePath)[1]
				self.data['filecontent'] = self.data['file'].read()
				
				if extension in self.parsers:
					self.data['filecontent'] = self.parsers[extension].parse(self.data['filecontent'])
			except:
				print(' ! "%s" could not be opened !' % filePath)
		else:
			fileDir = os.path.dirname(filePath)
			dirName = os.path.dirname(fileDir).strip()

			if not len(dirName):
				dirName = fileDir
			
			if len(dirName):
				if not os.path.exists(dirName):
					try: 	os.makedirs(dirName, exist_ok=True)
					except: print(' ! Could not create directory tree %s !' % (dirName))

			self.data['file'] = io.open(filePath, 'w', encoding='utf8')
			self.data['filecontent'] = ''
			self.data['filelen'] = 0

		try:
			self.data['line'] = re.split(r'[\n\r]', self.data['filecontent'])

			if len(self.data['line']) == 1 and not len(self.data['line'][0]):
				self.data['line'] = []
				self.data['filelen'] = 0
			else:
				self.data['filelen'] = len(self.data['line'])

		except:
			self.data['line'] = []
			self.data['filelen'] = 0

		if self.verbose: print(' %s line(s) read.' % len(self.data['line']))

	def _as(self, args):
		options = self.addSyntax('varName').parseArgs(args)
		self.setData('selection', options['varName'])
		return True

	# modules
	def _run(self, args):
		self.addSyntax('script')
		options = self.parseArgs(args)

		with open(options['script'], 'r', encoding='utf8') as scriptFile:
			script = scriptFile.read()
			lines = self.parse(script)
			self.lines[self.cmdLine:self.cmdLine] = lines

		self.setData('selection', False)
		self.setData('line', [])
		if 'found' in self.data:
			del self.data['found']

	# file operations
	def _empty(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args, '_empty')['what']

		if what:
			io.open(what, 'w', encoding='utf8')
			if self.verbose: print(' %s emptied out.' % what)
		else:
			self.setData('file', io.open(self.getData('filepath'), 'w', encoding='utf8'))
			self.setData('filelen', 0)
			if self.verbose: print(' %s emptied out.' % self.getData('filepath'))

	def _save(self, args):
		self.addSyntax('"as"', 'target')
		self.addDefaults({ 'target': self.getData('filepath') })
		target = self.parseArgs(args, '_save')['target']

		if not 'line' in self.data:
			self.setData('line', self.getData())

		self._empty([target])
		self._add(['[line]', 'to', target])

		if self.verbose: 
			print(' Saved %s as "%s".' % (self.getData('selection'), target))

	def _write(self, args):
		options = self.addSyntax('what').addDefaults({ 'what': 'found' }).parseArgs(args, '_write')
		what = options['what']
		return self._add(['[%s]' % options.findRef(what)])

	def _add(self, args):
		self.addSyntax('what', '"to"', 'to')
		self.addSyntax('what')
		options = self.parseArgs(args, '_add')
		
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

				if self.verbose:
					print(' %s saved in "%s". ' % (self.getData('selection'), self.getData('filename')))
			except: 
				print(' ! Could not write', self.getData('selection'), '!')
				pass

	def _bash(self, args):
		options = self.addClauses('as').addDefaults({'as':'selection'}).parseArgs(args, 'bash')

		self.setData(options['as'], subprocess.check_output(options.arguments))

	# memory
	def _be(self, args):
		prop = self.addSyntax('property').parseArgs(args, '_be')['property']
		setattr(self, prop, True)

	def _calculate(self, args):
		self.addClauses('as')
		self.addDefaults({'as':'result'})
		options = self.parseArgs(args, '_calculate')
		result = eval(' '.join(options.arguments))
		self.setData(options['as'], result)

	def _remember(self, args):
		self.addSyntax('what')
		self.addDefaults({ 'as': 'selection' })
		self.addClauses('as')
		options = self.parseArgs(args, '_remember')

		if not options['as']:
			options['as'] = options.referenced['what']

		self.setData(options['as'], options['what'])
		self._as([options['as']])

	# traversal
	def _find(self, args):
		self.addSyntax('"all"', 'what')
		self.addClauses('in')
		self.addDefaults({'in': self.getData('line')})

		options = self.parseArgs(args, '_findAll')

		stringOrRegEx = self.parseVars(options['what'])

		if stringOrRegEx in self.templates:
			stringOrRegEx = self.templates[stringOrRegEx]

		query = '%s' % stringOrRegEx

		if not isinstance(options['in'], list):
			options['in'] = [options['in']]

		if self.getData():
			self.data['line'] = [self.getData()]
		
		isString = options['what'] in options.literals
		
		if not isString:
			stringOrRegEx = r'' + str(stringOrRegEx)

		self.data['found'] = []
		self.data['group'] = []

		for lineNr, line in enumerate(options['in']):
			matches = []
			group = False

			if isString:
				if stringOrRegEx in line:
					matches = [stringOrRegEx]
			else:	
				matches = re.findall(stringOrRegEx, line, re.I)
				group = re.match(stringOrRegEx, line, re.I)

			if len(matches):
				self.data['found'].append([lineNr, line, matches])

			if group:
				self.data['group'].append([lineNr, group.groupdict()])

		if self.verbose: print(' found %s line(s) matching %s' % (len(self.getData('found')), query))

	def _select(self, args):
		self.addSyntax('"from"', 'from')
		self.addSyntax('"to"', 'to')
		self.addSyntax('"words"')
		self.addSyntax('which')
		self.addClauses('until','to', 'of')
		self.allowOrdinals('from','to','until','which')
		self.addDefaults({'from':0, 'to':None, 'until':None, 'of':self.getData()})
		options = self.parseArgs(args, '_select')

		of = options.findRef(options['of']) or options['of']

		if 'which' in options:
			try: self.setData(of, self.getData(of)[options['which']])
			except: print(' ! %s has no index %s ! ' % (of, options['which']))
		elif 'words' in options:
			self.setData(re.split(r'\b', self.getData()))
		else:
			if 'from' in options:
				if isinstance(options['from'], str):
					match = re.search(options['from'], self.getData(), re.I)
					
					if match: 	options['from'] = match.span()[0]
					else: 		options['from'] = 0

			if 'to' in options:	
				if isinstance(options['to'], str) and not options['to'] is None:
					match = re.search(options['to'], self.getData(), re.I)
					
					if match: 	options['to'] = match.span()[0]
					else: 		options['to'] = None

			self.setData(of, self.getData(of)[options['from']:options['to']])

	def _take(self, args):
		self.addSyntax('"lines|files|folders|results"')
		self.addDefaults({'as':'selection', 'in': self.getData('cwd')})
		self.addClauses('as', 'in')		

		options = self.parseArgs(args, '_take')
		varName = options.findRef(options['as']) or options['as']

		if 'lines' in options:
			if 'found' in self.data:
				self.setData(varName, [found[1] for found in self.data['found']])
			else:
				self.setData(varName, self.data['line'])
				self.setData('selection', varName)

		elif 'files' in options:
			if '.' in os.path.split(options['in'])[-1]:
				path = options['in']
			else:
				path = os.path.join(options['in'],'*.*')

			self.setData(varName, glob(path, recursive=True))
		elif 'folders' in options:
			foldersAndFiles = glob(os.path.join(options['in'], '*'), recursive=True)
			filesOnly = glob(os.path.join(options['in'], '*.*'), recursive=True)
			foldersOnly = list(set(foldersAndFiles) - set(filesOnly))

			self.setData(varName, foldersOnly)
		elif 'results' in options:
			collection = []

			for found in self.data['found']:
				if len(found[2]) > 1:
					for item in found[2]:
						collection.append(item)
				elif len(found[2]):
					collection.append(found[2][0])

			self.setData(varName, collection)

		if self.getData(varName) and len(self.getData(varName)) == 1:
			self.setData(varName, self.getData(varName)[0])

		#print('setting', varName, self.getData(varName))

	# manipulation
	def _extract(self, args):
		self.addSyntax('"timecode|duration"')
		self.addClauses('from', 'as')
		self.addDefaults({'as':'timecode'})
		options = self.parseArgs(args, '_extract')

		while len(options['from']) < 8:
			options['from'] += ':00'

		if len(options['from']) < 11:
			options['from'] += ',000'

		#if 'timecode' in options:
		#	timecode = self.__parseTimecode(options['from'])
		
		self.setData(options['as'], timecode)

	def _change(self, args):
		self.addSyntax('what','"to"','/formula/')
		options = self.parseArgs(args, '_change')

		if isinstance(options['what'], list):
			for i, item in enumerate(options['what']):
				varName = options.findRef(options['what'])
				self.data['i'] = i
				self.data['j'] = i + 1
				self.data['__' + varName] = item
				formula = self.parseVars(options['formula'].replace('[' + varName + ']', '[__' + varName + ']'))
				del self.data['__' + varName]
				self.data[varName][i] = formula
		else:
			rendered = self.parseVars(options['formula'])
			self.setData(options.findRef(options['what']), rendered)

	def _replace(self, args):
		self.addSyntax('what', '"by"', 'by')
		self.addDefaults({'in':self.getData('selection')})
		self.addClauses('in')
		options = self.parseArgs(args, '_replace')

		if not options['in']:
			data = self.getData('line')
			_in = 'line'
		else:
			data = options['in']
			_in = options.findRef(data)

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
		self.addSyntax('what')
		self.addDefaults({'delimiter': ';|,|\\' + os.sep})
		self.addClauses('as')

		options = self.parseArgs(args, '_split')

		if not 'as' in options:
			options['as'] = options['what']

		if isinstance(options['what'], bytes):
			options['what'] = str(options['what'], 'utf8')

		#self.setData('selection', options['as'])
		self.setData(options['as'], re.split(options['delimiter'], options['what']))

	def _count(self, args):
		self.addSyntax('"files|folders"')
		self.addSyntax('what')
		self.addClauses('as', 'in')
		self.addDefaults({'in':self.getData('cwd')})
		options = self.parseArgs(args, '_count')

		if 'files' in options:
			self.setData(options['as'], len(glob(os.path.join(options['in'], '*.*'), recursive=True)))
		elif 'folders' in options:
			foldersAndFiles = len(glob(os.path.join(options['in'], '*'), recursive=True))
			filesOnly = len(glob(os.path.join(options['in'], '*.*'), recursive=True))
			self.setData(options['as'], foldersAndFiles - filesOnly)
		elif 'what' in options:
			self.setData(options['as'], len(self.getData(options['what'])))

	def _combine(self, args):
		self.addSyntax('x', '"with"', 'y')
		self.addClauses('as')
		self.addDefaults({'as':'selection'})
		options = self.parseArgs(args, '_combine')

		self.setData(options['as'], options['x'] + options['y'])

	def _unique(self, args):
		self.addSyntax('what')
		self.addDefaults({'what':'line'})
		options = self.parseArgs(args, '_unique')

		noDupes = []
		if isinstance(options['what'], str):
			noDupes = [options['what']]
		else:
			[noDupes.append(i) for i in options['what'] if not noDupes.count(i)]

		if len(noDupes) == 1:
			noDupes = noDupes[0]
	
		self.setData(options.findRef(options['what']), noDupes)

	def _sort(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args, '_sort')['what']
		
		if what == 'lines':
			self.getData('line').sort()
		elif what:
			what.sort()

	def _reverse(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args, '_reverse')['what']
		if what == 'lines':
			self.getData('line').reverse()
		return what.reverse()

	# def _delete(self, filePath=''):
	# 	if not self.isActive(): return False
	# 	if len(filePath):
	# 		filePath = self.parseVars(filePath)
	
	# 		if os.path.exists(filePath):
	# 			os.remove(filePath)
	# 		else:
	# 			print(" File %s doesn't exist." % filePath)
	# 	else:
	# 		for lineNr, line, data in self.data['found']:
	# 			print(self.data['selection'], self.getData())
	# 			#del self.getData()[lineNr]

	def _remove(self, args):
		self.addSyntax('what')
		self.addSyntax('"empty"', '"lines|results|folders|files"')
		what = self.parseArgs(args, '_remove')['what']

		if what == 'lines':
			lines = self.getData('line')
			cleaned = []

			foundLines = [found[0] for found in self.data['found']]

			for lineNr, line in enumerate(lines):
				if lineNr not in foundLines:
					cleaned.append(line)

			self.setData('line', cleaned)

	#control flow
	def _for(self, args):
		options = self.addSyntax('"every"', 'collection').parseArgs(args, '_for')

		varName = options['collection']

		if isinstance(varName, list):
			varName = options.findRef(varName)
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

			collection = self.collections[-1]

			self.data['loops'] = len(collection)
			self.data['i'] = 0
			self.data['j'] = 1
			self.data['collection'] = collection
			self.data['selection'] = varName

			self.setData(varName, self.data['collection'][0])
		else:
			if self.verbose: print('', varName, 'empty, for loop not iterating!')

			while self.cmdLine < len(self.lines) and self.lines[self.cmdLine] != '---':
				self.cmdLine += 1
			#self.cmdLine -= 1

	def _repeat(self, args=False):
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
				self.cmdLine = self.scopes[-1] - 1
				self.setData(self.data['selection'], self.data['collection'][self.counters[-1]])
		else:
			self.cmdLine += 1
	
if len(sys.argv) > 1:
	taskFileName = sys.argv[1]

	TSL = TaskRunner(taskFileName)

	TSLPlugins = glob('tsl-plugins/*.py')

	if len(TSLPlugins):
		for TSLPlugin in TSLPlugins:
			exec(open(TSLPlugin, 'r', encoding='utf8').read())
	
	if TSL.task:
		print('Running "%s"...\n' % taskFileName)
		TSL.run()

else:
	print()
	