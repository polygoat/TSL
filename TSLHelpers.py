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

	def singular(self, word):
		if word in self.__irregulars.values():
			rev = {v: k for k, v in self.__irregulars.items()}
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

	def plural(self, word):
		if word in self.__irregulars.keys():
			return self.__irregulars[word]
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

Inflector = TSLInflector()

# hackaround for tail recursion (mainly for runLine)
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

