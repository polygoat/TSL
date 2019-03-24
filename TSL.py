#pip install timecode glob pprint
import io
import os
import re
import sys
import math
import subprocess
from timecode import Timecode
from glob import glob
from pprint import pprint

sys.path.append(os.getcwd())

from TSLCore import TaskRunnerCore

class TaskRunner(TaskRunnerCore):
	
	scopes = []
	counters = []
	collections = []
	selections = []

	templates = {
		'all': 			r'.*',
		'timecodes': 	r'(?P<hours>\d\d):(?P<minutes>\d\d)(?::(?P<seconds>\d\d)(?:\.(?P<milliseconds>\d\d\d)))?',
		'extension': 	r'\.([^.]+)$',
		'filename': 	r'(^|[\\/]+)([^\\/]+)$',
	}

	loopCancelled = False

	def __parseTimecode(self, timeCode, fps=1000):
		time = Timecode(fps, timeCode.replace(',','.'))
		return time

	def __renderTimecode(self, timeCode, delimiter=','):
		return str(timeCode).replace('.',delimiter)

	def _log(self, args):
		options = self.addSyntax('what').addDefaults({'what':'selection'}).parseArgs(args, '_log')

		what = options['what']

		if isinstance(what, dict):
			print(' %s:' % options.referenced['what'])
			pprint(what)
			print('\n')
		elif 'what' in options.referenced:
			if isinstance(what, Timecode):
				what = self.__renderTimecode(what) 

			if options.referenced['what'] == str(what):
				print('', what)
			elif what:
				if options.referenced['what']:
					print(' %s: %s' % (options.referenced['what'], what))
				else:	
					print('', what)
		else:
			print('', what)

	# clauses
	def _in(self, args):
		filePath = self.addSyntax('filePath').parseArgs(args)['filePath']

		self.setData('filepath', filePath)

		if not '.' in filePath:
			self.setData('cwd', filePath)
			try:		os.mkdir(filePath)
			except:		pass

			return

		if os.path.exists(filePath):
			self.data['file'] = io.open(filePath, 'r+', encoding='utf8')
		else:
			fileDir = os.path.dirname(filePath)
			
			if not os.path.exists(fileDir):
				try: 	os.makedirs(os.path.dirname(fileDir), exist_ok=True)
				except: pass

			self.data['file'] = io.open(filePath, 'w', encoding='utf8')

		try:
			self.data['line'] = re.split(r'[\n\r]', self.data['file'].read())
		except: pass

		if self.verbose: print(' %s lines read.' % len(self.data['line']))

	def _as(self, args):
		options = self.addSyntax('varName').parseArgs(args)
		self.setData('selection', options.referenced['varName'])
		return True

	# file operations
	def _empty(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args)['what']

		if what:
			io.open(what, 'w', encoding='utf8')
			if self.verbose: print(' %s emptied out.' % what)
		else:
			self.setData('file', io.open(self.getData('filepath'), 'w', encoding='utf8'))
			if self.verbose: print(' %s emptied out.' % self.__getData('filepath'))

	def _save(self, args):
		self.addSyntax('"as"', 'target')
		self.addDefaults({ 'target': self.getData('filepath') })
		target = self.parseArgs(args)['target']

		if not 'line' in self.data:
			self.setData('line', self.getData())

		self._empty([target])
		self._add(['line', 'to', target])

		if self.verbose: 
			print(' Saved %s as "%s".' % (self.getData('selection'), target))

	def _write(self, args):
		what = self.addSyntax('what').addDefaults({ 'what': 'found' }).parseArgs(args)['what']
		return self._add([what])

	def _add(self, args):
		self.addSyntax('what', '"to"', 'to')
		self.addSyntax('what')
		options = self.parseArgs(args)

		if options['what'] == 'found':
			content = [found[1] for found in self.getData(options['what'])]
		elif 'what' in options.quoted:
			content = options['what']
		else:
			content = self.getData(options['what'])

		if isinstance(content, list):
			try:
				content = '\n'.join(content)
			except: pass

		if 'to' in options:
			with io.open(options['to'], 'a', encoding='utf8') as target:
				target.write('%s\n' % content)
				target.close()
		else:
			try:
				self.data['file'].write('%s\n' % content)
				if self.verbose:
					print(' %s saved in "%s". ' % (self.getData('selection'), self.getData('filename')))
			except: 
				print(' ! Could not write', self.getData('selection'), '!')
				pass

	def _bash(self, args):
		options = self.addClauses('as').addDefaults({'as':'selection'}).parseArgs(args)

		self.setData(options['as'], subprocess.check_output(options.arguments))

	# memory
	def _be(self, args):
		prop = self.addSyntax('property').parseArgs(args)['property']
		setattr(self, prop, True)

	def _calculate(self, args):
		self.addClauses('as')
		self.addDefaults({'as':'result'})
		options = self.parseArgs(args)
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
		self.addDefaults({'in': 'line'})
		options = self.parseArgs(args, 'findAll')

		stringOrRegEx = self.parseVars(options['what'])

		if stringOrRegEx in self.templates:
			stringOrRegEx = self.templates[stringOrRegEx]

		query = '%s' % stringOrRegEx

		if not isinstance(options['in'], list):
			options['in'] = [options['in']]

		if self.getData():
			self.data['line'] = [self.getData()]
		
		isString = 'what' in options.quoted
		
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

		if self.verbose: print(' found %s lines matching %s' % (len(self.getData('found')), query))

	def _select(self, args):
		self.addSyntax('"from"', 'from')
		self.addSyntax('"to"', 'to')
		self.addSyntax('"words"')
		self.addSyntax('which')
		self.addClauses('until','to')
		self.allowOrdinals('from','to','until','which')
		self.addDefaults({'from':0, 'to':None, 'until':None})
		options = self.parseArgs(args, '_select')

		__counts = ['_', '_', 'one','two','three','four']

		#elif args[0] in __counts:
		#	args = ['to', str(__counts.index(args[0]))]

		if 'which' in options:
			try: self.setData(self.getData()[options['which']])
			except: print(' ! %s has no index %s ! ' % (self.data['selection'], options['which']))
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
				else:
					options['to'] += 1

			self.setData(self.getData()[options['from']:options['to']])

	def _take(self, args):
		self.addSyntax('"lines|files|folders|results"')
		self.addDefaults({'as':'selection', 'in':self.getData('cwd')})
		self.addClauses('as', 'in')
		options = self.parseArgs(args)
		varName = options['as']

		if 'lines' in options:
			if 'found' in self.data:
				self.setData(varName, [found[1] for found in self.data['found']])
			else:
				self.setData(varName, self.data['line'])

		elif 'files' in options:
			self.setData(varName, glob(os.path.join(options['in'],'*.*')))
		elif 'folders' in options:
			foldersAndFiles = glob(os.path.join(options['in'], '*'))
			filesOnly = glob(os.path.join(options['in'], '*.*'))
			foldersOnly = list(set(foldersAndFiles) - set(filesOnly))

			self.setData(varName, foldersOnly)
		elif 'results' in options:
			collection = []

			for found in self.data['found']:
				if len(found[2]) > 1:
					for item in found[2]:
						collection.append(item)
				else:
					collection.append(found[2][0])

			self.setData(varName, collection)
		
		if self.getData(varName) and len(self.getData(varName)) == 1:
			self.setData(varName, self.getData(varName)[0])

	# manipulation
	def _extract(self, args):
		self.addSyntax('"timecode|duration"')
		self.addClauses('from', 'as')
		self.addDefaults({'as':'timecode'})
		options = self.parseArgs(args)

		while len(options['from']) < 8:
			options['from'] += ':00'

		if len(options['from']) < 11:
			options['from'] += ',000'

		if 'timecode' in options:
			timecode = self.__parseTimecode(options['from'])
		
		self.setData(options['as'], timecode)

	def _change(self, args):
		self.addSyntax('what','"to"','/formula/')
		options = self.parseArgs(args, '_change')

		if isinstance(options['what'], list):
			for i, item in enumerate(options['what']):
				varName = options.referenced['what']
				self.data['i'] = i
				self.data['__' + varName] = item
				formula = self.parseVars(options['formula'].replace('[' + varName + ']', '[__' + varName + ']'))
				del self.data['__' + varName]
				self.data[varName][i] = formula
		else:
			rendered = self.parseVars(options['formula'])
			self.setData(options.referenced['what'], rendered)

	def _replace(self, args):
		self.addSyntax('what', '"by"', 'by')
		self.addDefaults({'in':self.getData('selection')})
		self.addClauses('in')
		options = self.parseArgs(args)

		if not options['in']:
			data = self.getData('line')
		else:
			data = options['in']

		_in = options.findRef(data)


		if isinstance(data, list):
			for i, entry in enumerate(data):
				if options['what'] in options.quoted:
					data[i] = entry.replace(options['what'], options['by'])
				else:
					data[i] = re.sub(options['what'], options['by'], entry, re.I)
			self.setData(_in, data)
		else:
			if options['what'] in options.quoted:
				self.setData(_in, data.replace(options['what'], options['by']))
			else:
				self.setData(_in, re.sub(options['what'], options['by'], data, re.I))

	def _split(self, args):
		self.addSyntax('what', '"by"', 'delimiter')
		self.addSyntax('what')
		self.addDefaults({'delimiter':','})
		self.addClauses('as')

		options = self.parseArgs(args, '_split')

		if not 'as' in options:
			options['as'] = options['what']

		options['as'] = options.findRef(options['as'])

		if isinstance(options['what'], bytes):
			options['what'] = str(options['what'], 'utf8')

		self.setData('selection', options['as'])
		self.setData(options['as'], re.split(options['delimiter'], options['what']))

	def _count(self, args):
		self.addSyntax('"files|folders"')
		self.addSyntax('what')
		self.addClauses('as', 'in')
		self.addDefaults({'in':self.getData('cwd')})
		options = self.parseArgs(args)

		if 'files' in options:
			self.setData(options['as'], len(glob(os.path.join(options['in'], '*.*'))))
		elif 'folders' in options:
			foldersAndFiles = len(glob(os.path.join(options['in'], '*')))
			filesOnly = len(glob(os.path.join(options['in'], '*.*')))
			self.setData(options['as'], foldersAndFiles - filesOnly)
		elif 'what' in options:
			self.setData(options['as'], len(self.getData(options['what'])))

	def _combine(self, args):
		self.addSyntax('x', '"with"', 'y')
		self.addClauses('as')
		self.addDefaults({'as':'selection'})
		options = self.parseArgs(args)

		self.setData(options['as'], options['x'] + options['y'])

	def _unique(self, args):
		self.addSyntax('what')
		self.addDefaults({'what':'line'})
		options = self.parseArgs(args, '_unique')

		noDupes = []
		[noDupes.append(i) for i in options['what'] if not noDupes.count(i)]

		if len(noDupes) == 1:
			noDupes = noDupes[0]
	
		self.setData(options.referenced['what'], noDupes)

	def _sort(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args)['what']
		
		if what == 'lines':
			self.getData('line').sort()
		elif what:
			what.sort()

	def _reverse(self, args):
		what = self.addSyntax('what').addDefaults({'what':False}).parseArgs(args)['what']
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
		what = self.addSyntax('what').parseArgs(args)['what']

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
		options = self.addSyntax('"every"', 'collection').parseArgs(args)
		collection = options['collection']
		varName = options.referenced['collection']

		if len(collection):
			self.scopes.append(self.cmdLine + 1)
			self.collections.append(self.getData(varName))
			self.selections.append(varName)
			self.counters.append(0)

			self.data['loops'] = len(self.collections[-1])
			self.data['i'] = 0
			self.data['collection'] = self.collections[-1]
			self.data['selection'] = varName

			self.setData(varName, self.data['collection'][0])
		else:
			if self.verbose: print('', varName, 'empty, for loop not iterating!')

			self.loopCancelled = True

			while self.lines[self.cmdLine] != '---':
				self.cmdLine += 1

	def _repeat(self, args=False):
		if self.loopCancelled: 
			self.loopCancelled = False
			return False

		try:
			self.counters[-1] += 1

			if self.data['i'] >= self.data['loops'] - 1:
				if len(self.collections):
					self.setData(self.collections[-1])
				
				self.scopes.pop()
				self.collections.pop()
				self.counters.pop()
				self.selections.pop()

				if self.counters[-1] > len(self.collections[-1]):
					self.cmdLine += 1
					return False

				if len(self.scopes) > 0:
					self.cmdLine = self.scopes[-1] - 1

					self.counters[-1] += 1
					self.data['collection'] = self.collections[-1]
					self.data['loops'] = len(self.collections[-1])
					self.data['i'] = self.counters[-1]
					self.data['selection'] = self.selections[-1]
				else:
					self.cmdLine += 1 
			else:		
				self.cmdLine = self.scopes[-1] - 1	
				self.data['i'] += 1
		
			if self.data['i'] < len(self.data['collection']):
				self.setData(self.data['collection'][self.data['i']])

		except: pass


if len(sys.argv) > 1:
	taskFileName = sys.argv[1]

	TK = TaskRunner(taskFileName)
	
	if TK.task:
		print('Running "%s"...\n' % taskFileName)
		TK.run()