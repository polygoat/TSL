import io
import os
import re
import json
import math
import subprocess
from .glob2 import glob
from TSL.TSLCore import TSLCore, TSLCollection
from TSL.TSLHelpers import TSLData, TSLArgs, TSLArg, TSLQuantifiers, TSLUtils

class TSLEngine(TSLCore):
	currentFile = ''

	scopes = []
	counters = []
	collections = []
	selections = []
	states = []
	looping = False

	templates = {
		'extension': 	r'\.([^.]+)$',
		'filename': 	r'(^|[\\/]+)([^\\/]+)$',
	}

	def _log(self, args):
		options = TSLArgs('log')
		options.supportSyntax(TSLArg('what', ...))
		options.parseArgs(args)

		what = options['what']

		if isinstance(what, str):
			what = TSLUtils.parseVars(what)

		whatReference = options.references.get('what', False)
		
		if isinstance(what, dict):
			self.log(' %s:' % options.references.get('what', 'what'))
			self.log(what)
			self.log('\n')
		elif whatReference:
			if len(whatReference):
				try:
					self.log(' %s: %s' % (whatReference, json.dumps(what, indent=4, sort_keys=True).replace('\n','\n ')))
				except UnicodeEncodeError:
					self.log(' ! %s could not be encoded for logging' % whatReference) 
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
		options = TSLArgs('in')
		options.supportSyntax(TSLArg('filePath', 'any'))
		options.parseArgs(args)
		if options.intercepted: return False

		filePath = options['filePath']
		self.currentFile = filePath

		TSLData['filepath'] = filePath
		TSLData['filename'] = os.path.basename(filePath)

		if not '.' in filePath:
			TSLData['cwd'] = filePath
			if not os.path.isdir(filePath):
				try:		
					os.mkdir(filePath)
					os.chdir(filePath)
				except:		
					self.log(" ! Couldn't create directory %s" % filePath)
			return

		extension = os.path.splitext(filePath)[1]

		if os.path.exists(filePath):
			try:
				TSLData['file'] = io.open(filePath, 'r+', encoding='utf8')
				TSLData['filecontent'] = TSLData['file'].read()
				
				if extension in self.parsers:
					TSLData['filecontent'] = self.parsers[extension].parse(TSLData['filecontent'])
			except:
				self.log(' ! "%s" could not be opened.' % filePath)
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
						self.log(' ! Could not create directory tree %s' % (dirName))

			TSLData['file'] = io.open(filePath, 'w', encoding='utf8')
			TSLData['filecontent'] = ''
			TSLData['filelen'] = 0

		try:
			if len(TSLData['filecontent']):
				TSLData['lines'] = TSLCollection(re.split(r'[\n\r]', TSLData['filecontent']))
			else:
				TSLData['lines'] = []

			if len(TSLData['lines']) == 1 and not len(TSLData['lines'][0]):
				TSLData['lines'] = []
				TSLData['filelen'] = 0
			else:
				TSLData['filelen'] = len(TSLData['lines'])

		except:
			TSLData['lines'] = []
			TSLData['filelen'] = 0

		if len(TSLData['lines']):
			TSLData['collection'] = TSLData['lines']

		if self.verbose: self.log(' %s line(s) read.' % len(TSLData['lines']))

	# modules
	def _run(self, args):
		options = TSLArgs('run').supportSyntax(TSLArg('script')).parseArgs(args)

		with open(options['script'], 'r', encoding='utf8') as scriptFile:
			script = scriptFile.read()
			lines = self.parse(script)
			del self.lines[self.cmdLine-1]
			self.lines[self.cmdLine-1:self.cmdLine-1] = lines
			self.cmdLine -= 1

	# file operations
	def _empty(self, args):
		options = TSLArgs('empty').supportSyntax().supportSyntax(TSLArg('what')).parseArgs(args)
		what = options['what']

		if what:
			io.open(what, 'w', encoding='utf8')
			if self.verbose: self.log(' %s emptied out.' % what)
		else:
			TSLData['file'] = io.open(TSLData['filepath'], 'w', encoding='utf8')
			TSLData['filelen'] = 0
			if self.verbose: self.log(' %s emptied out.' % TSLData['filepath'])

	def _save(self, args):
		options = TSLArgs('save')
		options.allowClauses(TSLArg('as'))
		options.setDefaults({ 'as': TSLData['filepath'] })
		target = options.parseArgs(args)['as']

		if not 'line' in TSLData:
			TSLData['line'] = TSLData['']

		self._empty([target])
		self._add(['[line]', 'to', target])

		if self.verbose: 
			self.log(' Saved %s as "%s".' % (TSLData['selection'], target))

	def _write(self, args):
		options = TSLArgs('write')
		options.supportSyntax('what').setDefaults({ 'what': '[found]' }).parseArgs(args)

		what = options['what']
		ref = options.references.get('what', 'what')
		if ref: 
			return self._add(['[%s]' % ref])
		return self._add([what])

	def _add(self, args):
		options = TSLArgs('add')
		options.supportSyntax(TSLArg('what'))
		options.allowClauses(TSLArg('to'))
		options.parseArgs(args)
		
		if options['what'] == 'found':
			content = [found[1] for found in TSLData[options['what']]]
		else:
			content = options['what']
		
		if isinstance(content, list):
			try:
				content = '\n'.join(content)
			except: pass

		if 'to' in options:
			with io.open(options['to'], 'a', encoding='utf8') as target:
				filePath = TSLData['filepath']
				extension = os.path.splitext(filePath)[1]
				
				if extension in self.parsers:
					target.close()
					self.parsers[extension].write(options['to'], content)
				else:
					target.write('%s\n' % content)
					target.close()
		else:
			try:
				if TSLData['filelen']:
					TSLData['file'].write('\n%s' % content)
				else:
					TSLData['file'].write('%s' % content)

				TSLData['filelen'] += len(content)

				if self.verbose:
					self.log(' %s saved in "%s". ' % (TSLData['selection'], TSLData['filename']))
			except: 
				self.log(' ! Could not write', TSLData['selection'])
				pass

	def _bash(self, args):
		options = TSLArgs('bash')
		options.supportSyntax(TSLArg('command', ...))
		options.allowClauses(TSLArg('as'))
		options.setDefaults({'as':'selection'})
		options.parseArgs(args)
		self.resolveAsClause(options['as'], subprocess.check_output(options['command']))

	# memory
	def _be(self, args):
		options = TSLArgs('be').supportSyntax(TSLArg('property')).parseArgs(args)
		prop = options['property']
		setattr(self, prop, True)

	def _calculate(self, args):
		options = TSLArgs('calculate')
		options.supportSyntax(TSLArg('all', ...))
		options.allowClauses(TSLArg('as'))
		options.setDefaults({'as':'result'})
		options.parseArgs(args)

		result = eval(' '.join(options['all']))
		self.resolveAsClause(options['as'], result)

	def _remember(self, args):
		options = TSLArgs('remember')
		options.supportSyntax(TSLArg('what', 'reference'))
		options.allowClauses(TSLArg('as'))
		options.parseArgs(args)	

		if not options['as']:
			options['as'] = options.references.get('what', 'selection')

		self.resolveAsClause(options['as'], options['what'])

	# traversal
	def _find(self, args):
		options = TSLArgs('find')
		options.supportSyntax(TSLArg('what', 'string'))
		options.allowClauses(TSLArg('in'))
		options.setDefaults({'in': '[collection]'})
		options.parseArgs(args)

		stringOrRegEx = TSLUtils.parseVars(options.what)

		if stringOrRegEx in self.templates:
			stringOrRegEx = self.templates[stringOrRegEx]

		query = '%s' % stringOrRegEx

		if not isinstance(options['in'], list):
			options['in'] = TSLCollection([options['in']])

		isString = 'what' in options.literals
		

		if stringOrRegEx in options.quantifiers:
			options['in'] = TSLQuantifiers.resolve(options.quantifiers[stringOrRegEx], options['in']).applyResults()
		
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

		options['in'].filter(checkMatch)

		if self.verbose: self.log(' found %s element(s) matching %s' % (len(TSLData['collection']), query))

	def _select(self, args):
		options = TSLArgs('select')
		options.supportSyntax('words')
		options.supportSyntax(TSLArg('which', 'ordinal'))
		options.supportSyntax(TSLArg('count', 'count'))
		options.allowClauses(TSLArg('from', 'ordinal'), TSLArg('to', 'ordinal'), TSLArg('until', 'ordinal'), TSLArg('after'),TSLArg('as'),TSLArg('of'))
		options.setDefaults({'from':0, 'to':None, 'until':None, 'of': '[collection]'})
		options.parseArgs(args)


		if options.until:
			options.to = options.until

		of = options.references.get('of', options.of)

		if len(of) == 1:
			of = of[0]

		if not 'as' in options and of:
			options['as'] = of

		if 'which' in options:
			options['from'] = options.which-1
			options['to'] = options.which
		elif 'count' in options:
				options['to'] = options['from'] + options.count - 1
		elif 'words' in options:
			TSLData[TSLData['selection']] = re.split(r'\b', TSLData[of])
		else:
			if 'after' in options:
				options['from'] = options.after		

			if 'from' in options:
				if isinstance(options['from'], str):
					match = re.search(options['from'], TSLData[''], re.I)
					matchLen = len(options['from'])
					
					if match: 	options['from'] = match.span()[0]
					else: 		options['from'] = 0

					if 'after' in options:
						options['from'] += matchLen - 1

			if 'to' in options:	
				if isinstance(options.to, str) and not options.to is None:
					match = re.search(options.to, TSLData[''], re.I)

					if match: 	options.to = match.span()[0]
					else: 		options.to = None
				elif isinstance(options.to, int):
					options.to += 1

			if options.to > len(TSLData[of]):
				options.to = None

		try:
			data = options.of[options['from']:options['to']]
			if len(data) == 1:
				data = data[0]
			self.resolveAsClause(options['as'], data)
		except: 
			if options['from'] == options['to']:
				self.log(' ! %s has no index %s' % (of, options['from']))
			else:
				self.log(' ! %s has no range %s to %s' % (of, options['from'], options['to']))

	def _take(self, args):
		options = TSLArgs('take')
		options.supportSyntax(TSLArg('what', ['lines','files','folders','results']))
		options.allowClauses(TSLArg('as'), TSLArg('in'))		
		options.setDefaults({'as':'collection', 'in': TSLData['cwd']})
		options.parseArgs(args)
		varName = options['as']

		if options.what == 'lines':
			collection = TSLData['collection']
			collection.setTo(collection.getFiltered(collection.lines))
			TSLData[varName] = collection

		elif options.what == 'files':
			if '.' in os.path.split(options['in'])[-1]:
				path = options['in']
			else:
				path = os.path.join(options['in'],'*.*')

			self.resolveAsClause(varName, glob(path))
		elif options.what == 'folders':
			foldersAndFiles = glob(os.path.join(options['in'], '*'), recursive=True)
			filesOnly = glob(os.path.join(options['in'], '*.*'), recursive=True)
			foldersOnly = list(set(foldersAndFiles) - set(filesOnly))

			TSLData[varName] = foldersOnly
		elif options.what == 'results':
			TSLData[varName] = TSLData['collection'].applyResults()

		if TSLData[varName] and len(TSLData[varName]) == 1:
			TSLData[varName] = TSLData[varName][0]

	# manipulation
	def _change(self, args):
		options = TSLArgs('change')
		options.supportSyntax(TSLArg('what', 'reference'))
		options.allowClauses(TSLArg('to', 'raw'))
		options.parseArgs(args)

		if isinstance(options.what, list):
			for i, item in enumerate(options.what):
				varName = options.references.get('what', 'what')
				TSLData['i'] = i
				TSLData['j'] = i + 1
				TSLData['__' + varName] = item
				formula = TSLUtils.parseVars(options['to'].replace('[' + varName + ']', '[__' + varName + ']'))
				del TSLData['__' + varName]
				TSLData[varName][i] = formula
		else:
			rendered = TSLUtils.parseVars(options['to'])
			TSLData[options.references.get('what', 'what')] = rendered

	def _replace(self, args):
		options = TSLArgs('replace')
		options.supportSyntax(TSLArg('what'))
		options.allowClauses(TSLArg('by'), TSLArg('in'))
		options.setDefaults({'in':'[collection]'})
		options.parseArgs(args)

		data = options['in']
		_in = options.references.get(data, data)

		if not _in:
			_in = data
			data = TSLData[data]
			options['in'] = data

		if isinstance(data, list):
			for i, entry in enumerate(data):
				if 'what' in options.literals:
					data[i] = entry.replace(options.what, options.by)
				else:
					data[i] = re.sub(r'' + options.what, r'' + options.by, entry, re.I)
			TSLData[_in] = data
		else:
			if 'what' in options.literals:
				TSLData[_in] = data.replace(options.what, options.by)
			else:
				TSLData[_in] = re.sub(options.what, options.by, data, re.I)

	def _split(self, args):
		options = TSLArgs('split')
		options.supportSyntax(TSLArg('what', 'reference','string'))
		options.allowClauses(TSLArg('as','string'), TSLArg('by'))
		options.setDefaults({ 'what': TSLData[''] })
		options.parseArgs(args)

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

		if not options['as']:
			options['as'] = options.references.get('what', 'collection')

		if not 'by' in options:
			if self.currentFile.endswith('.tsv'):
				options['by'] = r'\t'
			elif self.currentFile.endswith('.csv'):
				options['by'] = r','
			else:
				options['by'] = r';|,|' + re.escape(os.sep)
		elif __byTerms.get(options['by']):
			options['by'] = __byTerms.get(options['by'])
		elif __byTerms.get(options['by'][:-1]):
			options['by'] = __byTerms.get(options['by'][:-1])

		if isinstance(options['what'], bytes):
			options['what'] = str(options['what'], 'utf8')

		results = re.split(options['by'], options['what'])
		results = list(filter(None, results))

		self.resolveAsClause(options['as'], results)

	def _count(self, args):
		options = TSLArgs('count')
		options.supportSyntax(TSLArg('what', 'reference'))
		options.supportSyntax(TSLArg('which', ['files', 'folders']))
		options.allowClauses(TSLArg('as'), TSLArg('in'))
		options.setDefaults({'in':TSLData['cwd']})
		options.parseArgs(args)

		if 'what' in options:
			self.resolveAsClause(options['as'], len(options['what']))
		elif options['which'] == 'files':
			self.resolveAsClause(options['as'], len(glob(os.path.join(options['in'], '*.*'), recursive=True)))
		elif options['which'] == 'folders':
			foldersAndFiles = len(glob(os.path.join(options['in'], '*'), recursive=True))
			filesOnly = len(glob(os.path.join(options['in'], '*.*'), recursive=True))
			self.resolveAsClause(options['as'], foldersAndFiles - filesOnly)

	def _combine(self, args):
		options = TSLArgs('combine')
		options.supportSyntax(TSLArg('x', 'reference'), 'with', TSLArg('y', 'reference'))
		options.allowClauses(TSLArg('as'))
		options.setDefaults({'as':'selection'})
		options.parseArgs(args)

		self.resolveAsClause(options['as'], options['x'] + options['y'])

	def _unique(self, args):
		options = TSLArgs('unique')
		options.supportSyntax(TSLArg('what', 'reference'))
		options.setDefaults({'what':'[collection]'})
		options.parseArgs(args)

		noDupes = []
		if isinstance(options['what'], str):
			noDupes = [options['what']]
		else:
			[noDupes.append(i) for i in options['what'] if not noDupes.count(i)]

		if len(noDupes) == 1:
			noDupes = noDupes[0]
	
		TSLData[options.references.get('what', 'what')] = noDupes

	def _sort(self, args):
		options = TSLArgs('sort')
		options.supportSyntax('what')
		options.setDefaults({'what':False})
		options.allowClauses(TSLArg('by'))
		options.parseArgs(args)
		what = options['what']

		if what == 'lines':
			TSLData['collection'].sort()
		elif what:
			if 'by' in options:
				items = what + []
				what.sort(key=lambda item: options['by'][items.index(item)])
			else:
				what.sort()

	def _reverse(self, args):
		options = TSLArgs('reverse')
		options.supportSyntax(TSLArg('what', 'reference', 'string'))
		options.setDefaults({'what':False})
		options.parseArgs(args, 'reverse')
		what = options['what']
		
		if what == 'lines':
			TSLData['collection'].reverse()
		return what.reverse()

	def _remove(self, args):
		options = TSLArgs('remove')
		options.supportSyntax(TSLArg('what'))
		options.supportSyntax('empty', TSLArg('which', ['folders','files']))
		options.parseArgs(args)
		what = options.get('what', '')

		forRemoval = TSLData['collection'].lineNrs.copy()

		if what == 'lines':
			def checkKeeping(entry, id):
				if id not in forRemoval:
					return entry
				return False
			collection = TSLData['collection'].filter(checkKeeping).applyResults()
			TSLData['collection'] = collection
		elif 'which' in options:
			if options['which'] == 'folders':
				filesAndFolders = glob('*', recursive=True)
				for item in filesAndFolders:
					if os.path.isdir(item):
						try:	os.rmdir(item)
						except: pass
			else:
				files = glob('**/*', recursive=True)
				emptyFiles = list(filter(lambda file: not os.stat(file).st_size, files))
				
				for file in emptyFiles:
					os.remove(file)

	#control flow
	def _for(self, args):
		options = TSLArgs('for')
		options.supportSyntax(TSLArg('collection', 'reference'))
		options.parseArgs(args)
		varName = options['collection']

		if 'collection' in options.references:
			varName = options.references.get('collection')
		else:
			varName = varName[1:-1]

		collection = TSLCollection(TSLData[self.toPlural(varName)])

		if '[%s]' % varName in options.quantifiers:
			quantifiers = options.quantifiers['[%s]' % varName]
			collection = TSLQuantifiers.resolve(quantifiers, collection).results

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

			TSLData['loops'] = len(collection)
			TSLData['i'] = 0
			TSLData['j'] = 1
			TSLData['collection'] = collection
			TSLData['selection'] = varName

			TSLData[varName] = TSLData['collection'][0]
		else:
			if self.verbose: self.log('', varName, 'empty, for loop not iterating!')

			self.looping = False

			while self.cmdLine < len(self.lines) and self.lines[self.cmdLine] != '---':
				self.cmdLine += 1

	def _repeat(self, args=False):
		options = TSLArgs('repeat').parseArgs(args)
		if len(self.scopes):

			if not self.states[-1]:
				self.states[-1] = True
				return False

			self.counters[-1] += 1
			TSLData['i'] = self.counters[-1]
			TSLData['j'] = TSLData['i'] + 1

			if self.counters[-1] >= len(self.collections[-1]):
				TSLData[self.selections[-1]] = self.collections[-1]
				self.scopes.pop()
				self.counters.pop()
				self.selections.pop()
				self.collections.pop()
				self.states.pop()

				if len(self.collections):
					TSLData['collection'] = self.collections[-1]
					TSLData['selection'] = self.selections[-1]
					TSLData['i'] = self.counters[-1]
					TSLData['j'] = self.counters[-1] + 1
				else:
					try:
						del TSLData[TSLData['selection']]
					except:
						...
					self.looping = False
			else:		
				self.cmdLine = self.scopes[-1] - 1
				TSLData[TSLData['selection']] = TSLData['collection'][self.counters[-1]]
		else:
			self.looping = False
			self.cmdLine += 1
			