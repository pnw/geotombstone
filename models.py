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
class SearchableDate(ndb.Model):
	'''
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
# 		return '{}/photo/{}?p={}'.format(utils.BASE_URL,self.key.parent().id(),self.key.id())
		return '{}/photo/{}?p={}'.format("",self.key.parent().id(),self.key.id())
class Obituary(BaseModel):
	'''
	A record of someones tombstone
	'''
	ghash = ndb.StringProperty(required = True)
	name = ndb.StringProperty()
	dob = ndb.DateProperty() # date of birth
	dod = ndb.DateProperty() # date of death
	pob = ndb.StringProperty() # place of birth
	pod = ndb.StringProperty() # place of death
	uploader_key = ndb.KeyProperty(AppUser)
	tombstone_message = ndb.TextProperty()
	
	dob_searchable = ndb.StructuredProperty(SearchableDate)
	dod_searchable = ndb.StructuredProperty(SearchableDate)
	tags = ndb.ComputedProperty(
							lambda self: utils.tokenize_multi(
															self.name,
															self.pob,
															self.pod
															),
							repeated=True)
	
	ghash_list = ndb.ComputedProperty(lambda self: utils.listify_ghash(self.ghash),
									repeated = True)
	def _pre_put_hook(self):
		if self.dob:
			self.dob_searchable = self.searchatize_date(self.dob)
		if self.dod:
			self.dod_searchable = self.searchatize_date(self.dod)
	@property
	def dob_web(self):
		return '{}/{}/{}'.format(self.dob.month,self.dob.day,self.dob.year)
	@property
	def dod_web(self):
		return '{}/{}/{}'.format(self.dod.month,self.dod.day,self.dod.year)
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
		return Message.query().iter(keys_only=True)
	@property
	def narrative_keys(self):
		return Narrative.query().iter(keys_only=True)
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
	def package(self,uploader = None,messages = None, narratives = None,web=False):
		'''
		Packages an obituary into a dict for the phone
		@rtype: dicts
		'''
		to_return = {
					'oid' : self.key.id(),
					'geo_point' : self.geo_point,
					'name' : self.name or '',
					'dob' : str(self.dob or '') if web is False else str(self.dob_web() or ''),
					'dod' : str(self.dod or '') if web is False else str(self.dod_web() or ''),
					'pob' : self.pob or '',
					'pod' : self.pod or '',
					'tombstone_message' : self.tombstone_message or '',
					'photo_urls' : self.get_photo_urls(),
					'obituary_url' : '{}/obituary/{}'.format(utils.BASE_URL,self.key.id()),
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
