import logging
import sys,traceback
from lib.nltk.stem.porter import PorterStemmer
from lib.nltk.tokenize.regexp import WhitespaceTokenizer
import string
import os

if os.environ['SERVER_SOFTWARE'].startswith('Development') == True:
	BASE_URL = 'http://0.0.0.0:8088'
else:
	BASE_URL = 'http://geotombstone.appspot.com'

def log_error(message=''):
	_,_,exc_trace = sys.exc_info()
	logging.error(traceback.format_exc(exc_trace))
	if message:
		logging.error(message)

def tokenize(text):
	'''
	Tokenizes and stems a string
	'''
	text = text.encode('ascii','replace')
	# chars to be converted to space
	exclude = ['_','/',',','-','|',' ']
	# remove punctuation
	for punct in string.punctuation:
		if punct not in exclude:
			text = text.replace(punct,'')
	
	# replace special chars with spaces
	for c in exclude:
		text = text.replace(c, ' ')
	
	# tokenize the string
	tokenizer = WhitespaceTokenizer()
	stemmer = PorterStemmer()
	tokens = [stemmer.stem(t.lower()) for t in tokenizer.tokenize(text)]
	return tokens
def tokenize_multi(*args):
	text = ' '.join(filter(None,args))
	return tokenize(text)

def listify_ghash(ghash):
	'''
	Converts a string ghash into a list of all possible sub-ghashes
	@param ghash: ghash
	@type ghash: str
	@return: a list of sub-ghashes
	@rtype: list
	'''
	return [ghash[:idx] for idx in range(1,len(ghash)+1)]
	
	