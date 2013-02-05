from google.appengine.ext import ndb
from lib.nltk.stem.porter import PorterStemmer
from lib.nltk.tokenize.regexp import WhitespaceTokenizer
import logging
import models
import os
import string
import sys
import traceback

if os.environ['SERVER_SOFTWARE'].startswith('Development') == True:
	BASE_URL = 'http://0.0.0.0:8088'
else:
	BASE_URL = 'http://geotombstone.com'

def log_error(message=''):
	_,_,exc_trace = sys.exc_info()
	logging.error(traceback.format_exc(exc_trace))
	if message:
		logging.error(message)

def tokenize(text):
	'''
	Tokenizes and stems a string
	'''
	logging.info('tokenizing: '+str(text))
	if text is None:
		return None
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

	
def search(search_tokens=None,dob=None,dod=None,ghashes=None,ghash_precision=4):
	'''
	Searches obituaries given the following parameters
	@param search_tokens: a list of search tokens
	@type search_tokens: list
	@param dob: date of birth
	@type dob: datetime.date
	@param dod: date of death
	@type dod: datetime.date
	@return: a list of obituary entities
	@rtype: list
	'''
	logging.info('in search: ')
	logging.info(search_tokens)
	logging.info('dob: '+str(dob))
	logging.info('dod: '+str(dod))
	qry = models.Obituary.query()
	if search_tokens:
		assert isinstance(search_tokens,list)
		# combine all the tokens into one list for later when we count match freq.
		qry = qry.filter(models.Obituary.tags.IN(search_tokens))
	if dob:
		qry = qry.filter(
						models.Obituary.dob_searchable.year == dob.year,
						models.Obituary.dob_searchable.month == dob.month
						)
	if dod:
		qry = qry.filter(
						models.Obituary.dod_searchable.year == dod.year,
						models.Obituary.dod_searchable.month == dod.month
						)
	if ghashes:
		# pare down ghashes into the desired size
		ghashes = [gh[:ghash_precision] for gh in ghashes]
		# filter on ghashes
		qry = qry.filter(
						models.Obituary.ghash_list.IN(ghashes)
						)
	obit_keys = qry.iter(keys_only = True)
	obit_futures = ndb.get_multi_async(obit_keys)
	obits = (o.get_result() for o in obit_futures)
	
	# sort the obituaries by the number of matched tags
	if search_tokens:
		obits = sorted(obits,
					key = lambda o: o.count_tag_matches(search_tokens),
					reverse = True)
	return obits