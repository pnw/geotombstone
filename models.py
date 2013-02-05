from google.appengine.ext import ndb
from geo import geohash
import utils
import logging
class BaseModel(ndb.Model):
	pass

class AppUser(BaseModel):
	'''
	A user account on the phone
	'''
	name = ndb.StringProperty(required=True)
	email = ndb.StringProperty(required=True)
	phone = ndb.StringProperty()
	address = ndb.StringProperty()
	def package(self):
		return self.to_dict()
class PasswordProperty(ndb.Model):
	pw = ndb.StringProperty(required = True,indexed = False)
	salt = ndb.StringProperty(required = True,indexed = False)
class WebUser(BaseModel):
	'''
	A user account on the website
	'''
	email = ndb.StringProperty(required = True)
	pw = ndb.StructuredProperty(PasswordProperty,required = True,indexed = False)
	@ndb.transactional
	def add_bookmark(self,obit_id):
		Bookmark.get_or_insert(obit_id,parent=self.key)
	@ndb.transactional
	def remove_bookmark(self,obit_id):
		ndb.Key(Bookmark,obit_id,parent=self.key).delete()
		
		
class Bookmark(ndb.Model):
	'''User bookmarks an obituary'''
class SearchableDate(ndb.Model):
	'''Date in a format that can searched without inequalities
	'''
	year = ndb.IntegerProperty()
	month = ndb.IntegerProperty()
	day = ndb.IntegerProperty()
class Photo(BaseModel):
	'''
	A photo attatched to the obituary
	'''
	img_key = ndb.BlobKeyProperty()
	def _pre_put_hook(self):
		'''Assure the photo is attached to something'''
		assert self.key.parent()
	@property
	def img_url(self):
		return '{}/photo/{}?p={}'.format(utils.BASE_URL,self.key.parent().id(),self.key.id())
#		return '{}/photo/{}?p={}'.format("",self.key.parent().id(),self.key.id())
class Obituary(BaseModel):
	'''
	A record of someones tombstone
	'''
	
	name = ndb.StringProperty()
	name_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.name),repeated = True)
	
	dob = ndb.DateProperty() # date of birth
	dob_searchable = ndb.StructuredProperty(SearchableDate)
	
	dod = ndb.DateProperty() # date of death
	dod_searchable = ndb.StructuredProperty(SearchableDate)
	
	pob = ndb.StringProperty() # place of birth
	pob_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.pob),repeated = True)
	
	pod = ndb.StringProperty() # place of death
	pod_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.pod),repeated = True)
	
	ghash = ndb.StringProperty(required = True)
	ghash_list = ndb.ComputedProperty(lambda self: utils.listify_ghash(self.ghash),repeated = True)
	
	mothers_name = ndb.StringProperty()
	mothers_name_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.mothers_name),repeated = True)
	
	fathers_name = ndb.StringProperty()
	fathers_name_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.fathers_name),repeated = True)
	
	cod = ndb.StringProperty() # cause of death
	cod_tags = ndb.ComputedProperty(lambda self: utils.tokenize(self.cod),repeated = True)
	
	uploader_key = ndb.KeyProperty(AppUser)
	tombstone_message = ndb.TextProperty()
	
	tags = ndb.ComputedProperty(
							lambda self: utils.tokenize_multi(
															self.name,
															self.pob,
															self.pod
															),
							repeated=True)
	
	def fetch_related(self):
		'''
		Fetches obituaries that are related to this one for each field
		'''
		keys = {
			'name' : [],
			'pob' : [],
			'pod' : [],
			'mothers_name' : [],
			'fathers_name' : [],
			'cod' : [],
			'dob' : [],
			'dod' : [],
			}
		if self.name_tags:
			keys['name'] = Obituary.query(Obituary.name_tags.IN(self.name_tags)).iter(keys_only=True)
		if self.pob_tags:
			keys['pob'] = Obituary.query(Obituary.pob_tags.IN(self.pob_tags)).iter(keys_only=True)
		if self.pod_tags:
			keys['pod'] = Obituary.query(Obituary.pod_tags.IN(self.pod_tags)).iter(keys_only=True)
		if self.mothers_name_tags:
			keys['mothers_name'] = Obituary.query(Obituary.mothers_name_tags.IN(self.mothers_name_tags)).iter(keys_only=True)
		if self.fathers_name_tags:
			keys['fathers_name'] = Obituary.query(Obituary.fathers_name_tags.IN(self.fathers_name_tags)).iter(keys_only=True)
		if self.cod_tags:
			keys['cod'] = Obituary.query(Obituary.cod_tags.IN(self.cod_tags)).iter(keys_only=True)
		if self.dob:
			keys['dob'] = Obituary.query(Obituary.dob == self.dob).iter(keys_only=True)
		if self.dod:
			keys['dod'] = Obituary.query(Obituary.dod == self.dod).iter(keys_only=True)
		# fetch the entity futures
		related_count = 0
		relative_futures = {}
		for field,key_list in keys.iteritems():
			key_list = filter(lambda k: k != self.key,key_list)
			related_count += key_list.__len__()
			relative_futures[field] = ndb.get_multi_async(key_list)
		
		# fetch the entities
		relatives = {}
		for field,futures in relative_futures.iteritems():
			relatives[field] = (f.get_result() for f in futures)
		return related_count,relatives

	def _pre_put_hook(self):
		if self.dob:
			self.dob_searchable = self.searchatize_date(self.dob)
		if self.dod:
			self.dod_searchable = self.searchatize_date(self.dod)
	@property
	def dob_web(self):
		if self.dob:
			return '{}/{}/{}'.format(self.dob.month,self.dob.day,self.dob.year)
		else:
			return ''
	@property
	def dod_web(self):
		if self.dod:
			return '{}/{}/{}'.format(self.dod.month,self.dod.day,self.dod.year)
		else:
			return ''
	@staticmethod
	def fetch_author_multi(obits):
		'''
		Fetches the authors from a list of obituaries
		@param obits: a list of obituaries
		@type obits: list
		@return: a generator for the authors of each obit
		@rtype: generator
		'''
		uploader_keys = [ob.uploader_key for ob in obits]
		uploader_futures = ndb.get_multi_async(uploader_keys)
		uploaders = (f.get_result() for f in uploader_futures)
		return uploaders
	@property
	def message_keys(self):
		return Message.query(ancestor = self.key).iter(keys_only=True)
	@property
	def narrative_keys(self):
		return Narrative.query(ancestor = self.key).iter(keys_only=True)
	@staticmethod
	def fetch_messages_multi(obits):
		return _fetch_attached_multi_prop_multi(obits, 'message_keys')
	@staticmethod
	def fetch_narratives_multi(obits):
		return _fetch_attached_multi_prop_multi(obits, 'narrative_keys')
	@property
	def key_id(self):
		return self.key.id()
	@property
	def geo_point(self):
		'''
		@return: the obituarys geo_point
		@rtype: dict
		'''
		lat,lon = geohash.decode(self.ghash)
		return {
			'lat' : lat,
			'lon' : lon
			}
	@property
	def photos(self):
		return Photo.query(ancestor = self.key).iter()
	def get_photo_urls(self):
		return [i.img_url for i in self.photos]
	@property
	def obituary_url(self):
		return '{}/obituary/{}'.format(utils.BASE_URL,self.key.id())
	def package(self,uploader = None,messages = None, narratives = None,web=False):
		'''
		Packages an obituary into a dict for the phone
		@rtype: dicts
		'''
		to_return = {
					'oid' : self.key.id(),
					'geo_point' : self.geo_point,
					'name' : self.name or '',
					'dob' : str(self.dob or '') if web is False else self.dob_web,
					'dod' : str(self.dod or '') if web is False else self.dod_web,
					'pob' : self.pob or '',
					'pod' : self.pod or '',
					'tombstone_message' : self.tombstone_message or '',
					'photo_urls' : self.get_photo_urls(),
					'obituary_url' : self.obituary_url,
					'uploader' : uploader if uploader is not None else {},
					'messages' : messages if messages is not None else [],
					'narratives' : narratives if narratives is not None else [],
					}
		return to_return
	def count_tag_matches(self,search_tokens):
		'''
		Counts the number of obituary tags that match a list
		of search tags
		@param search_tokens: a list of search tags
		@type search_tokens: list
		@return: the number of tag matches
		@rtype: int
		'''
		return filter(lambda tag: tag in search_tokens,self.tags).__len__()
		
	@staticmethod
	def searchatize_date(day):
		'''
		Converts an ndb.DateProperty into a searchable json
		@param d: a date object
		@type d: datetime.date
		@return: a searchable version of the date
		@rtype: SearchableDate
		'''
		d = SearchableDate(
						year=day.year,
						month=day.month,
						day=day.day
						)
		logging.info(d)
		return d
	
		
		
class Message(BaseModel):
	'''
	A message to loved ones
	'''
	message = ndb.TextProperty(required = True)
	author_key = ndb.KeyProperty()
	author_name = ndb.StringProperty()
	def _pre_put_hook(self):
		'''Assure the message has a parent Obituary'''
		assert self.key.parent(), 'Message needs a parent'
	def package(self):
		return self.to_dict(include=('message','author_name'))
class Narrative(BaseModel):
	'''
	A narrative about the deceased person
	'''
	message = ndb.TextProperty(required = True)
	author_key = ndb.KeyProperty()
	author_name = ndb.StringProperty()
	def _pre_put_hook(self):
		'''Assure the narrative has a parent Obituary'''
		assert self.key.parent(), 'Narrative needs a parent'
	def package(self):
		return self.to_dict(include=('message','author_name'))
def _fetch_attached_multi_prop_multi(entities,attr):
	'''
	Used for batch fetching referenced properties from a list of entities
	@param entities: a list of model instances
	@type entities: list
	@param attr: a property on those entities that is a list of keys
	@type attr: str
	@return: a list of lists of all entities attached to each entity
	'''
	keys_lists = [getattr(ent, attr) for ent in entities]
	futures_lists = [ndb.get_multi_async(keys) for keys in keys_lists]
	prop_lists = ((f.get_result() for f in l) for l in futures_lists)
	return prop_lists
