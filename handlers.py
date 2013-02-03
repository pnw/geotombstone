from gaesessions import get_current_session
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers
import datetime
import hashlib
import json
import logging
import models
import utils
import uuid
import webapp2

class BaseHandler(webapp2.RequestHandler):
	class SessionError(Exception):
		'''Session is invalid'''
	class InputError(Exception):
		'''Input is invalid'''
	def say(self,stuff=''):
		'''For debugging
		'''
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('\n')
		self.response.out.write(stuff)
	def get_by_id(self,model,id_):
		'''
		Wrapper for model.get_by_id to assure that id is always int
		@param model: the model
		@type model: ndb.Model
		@param id_: model id
		@type id_: str or int
		'''
		return model.get_by_id(int(id_))
		
	def rget(self,key,predicate=None,required = False):
		'''
		I hate typing out self.request.get all the time
		@param key: http request param
		@type key: str
		@param predicate: action to perform on the input val
		@type predicate: type or function
		@param required: Whether or not the param is required
		@type required: bool
		@return: val for the request param
		
		@rtype: str
		
		@raise self.InputError: if the input is invalid
		'''
		if predicate is None:
			predicate = str
		val = self.request.get(key)
		logging.info('{}: {}'.format(key,val))
		if required is True and not val:
			e = '{}: required'.format(key)
			raise self.InputError(e)
		else:
			# typecast the input
			try:
				val = predicate(val)
			except ValueError,e:
				raise self.InputError('{}: {}'.format(key,e.message))
			else:
				return val or None
	def send_server_error(self,status_message='Server Error.'):
		'''
		Special response indicating a server error
		@param status_message: Message to describe what went wrong
		@type status_message: str
		'''
		utils.log_error()
		# 500 == sever error
		return self.send_response(500, status_message)
	def send_success(self,response):
		'''
		Special response indicating success
		@param response: response data
		@type response: dict
		'''
		# 200 == OK
		return self.send_response(200,'OK',response)
	def send_response(self,code,message,response=None):
		'''
		Generic response method
		@param code: http status code
		@type code: int
		@param message: status message
		@type message: str
		@param response: json-able dict
		@type response: dict
		'''
		reply = {
				'status':{
					'code' : code,
					'message' : str(message)
					}
				}
		if response is not None:
			reply['response'] = response
		
		try:
			to_write = json.dumps(reply)
		except TypeError,e:
			return self.send_server_error(e.message)
		else:
			return self.response.out.write(to_write)
	
	def full_search(self):
		'''
		Provides a common method to perform a search on api and website
		
		@warning: should be wrapped in a try,except block
		@return: a list of obituaries
		@rtype: list
		'''
		name =  self.rget('name',str) or None
		pob = self.rget('pob',str) or None
		pod = self.rget('pod',str) or None
		
		# join the string params together if they exist
		search_tokens = utils.tokenize_multi(name,pob,pod)
		logging.info(search_tokens)
		dob = self.rget('dob',self.parse_date) or None
		dod = self.rget('dod',self.parse_date) or None
		
		logging.info('Sending to search: ')
		logging.info(search_tokens)
		
		return utils.search(search_tokens, dob, dod)
		
		
	
	def create_entity(self,model,parent_key=None,**params):
		'''
		Creates an entity using transaction
		@param model: model class
		@type model: ndb.Model
		@param parent_key: the parent's key
		@type parent_key: ndb.Key
		@return: the newly created entity
		@rtype: model
		'''
		@ndb.transactional
		def create(id_,parent_key,**params):
			ent = model(id=id_,parent=parent_key,**params)
			ent.put()
			return ent
		id_,_ = model.allocate_ids(1)
		return create(
					id_,
					parent_key,
					**params
					)
class WebHandler(BaseHandler):
	'''
	For the web needs
	'''
	def log_in(self,uid,session = None):
		if session is None:
			session = get_current_session()
		session['uid'] = uid
		return session
	def log_out(self,session = None):
		if session is None:
			session = get_current_session()
		session.terminate()
		return session
	def get_user_from_session(self,session=None):
		if session is None:
			session = get_current_session()
		try:
			uid = session['uid']
		except KeyError:
			user = None
		else:
			user = models.WebUser.get_by_id(uid)
		return user
	def hash_password(self,pw,salt=None):
		'''
		Hashes a password using a salt and hashlib
		http://stackoverflow.com/questions/9594125/salt-and-hash-a-password-in-python
		@param pw: the users password
		@type pw: str
		@return: hashed_password (str), salt (str)
		@rtype: tuple
		'''
		if salt is None:
			salt = uuid.uuid4().hex
		hashed_password = hashlib.sha512(pw + salt).hexdigest()
		return hashed_password,salt
	def create_web_user(self,email,pw):
		'''
		Creating a new web user
		@param email: the users email
		@type email: str
		@param pw: the **UNHASHED** password
		@type pw: str
		@return: the new users key
		@rtype: ndb.Key
		'''
		hashed_pw, salt = self.hash_password(pw)
		return self.create_entity(models.WebUser,
								email = email,
								pw = models.PasswordProperty(
															pw=hashed_pw,
															salt=salt
															)
								)
	def parse_date(self,date_str):
		'''
		Parses a date string into a datetime.date object
		@param date_str: date in format yyyy-mm-dd
		@type date_str: str
		@return: date
		@rtype: datetime.date
		@raise self.InputError: if date_str is not valid
		'''
		if date_str:
			mm,dd,yyyy = [int(i) for i in date_str.split('/')]
			d = datetime.date(yyyy,mm,dd)
			return d
		else:
			return None
class APIHandler(BaseHandler):
	'''
	For the api needs
	'''
	def create_obituary(self,**params):
		'''
		Creates an obituary, wrapping around self.create_entity
		@return: obituary entity
		@rtype: models.Obituary
		'''
		img_keys = params.pop('img_keys')
		
		# create the obituary
		ob = self.create_entity(models.Obituary, **params)
		# add the image as a child
		for key in img_keys:
			self.create_entity(models.Photo,ob.key,img_key=key)
		return ob
	def parse_date(self,date_str):
		'''
		Parses a date string into a datetime.date object
		@param date_str: date in format yyyy-mm-dd
		@type date_str: str
		@return: date
		@rtype: datetime.date
		@raise self.InputError: if date_str is not valid
		'''
		if date_str:
			yyyy,mm,dd = [int(i) for i in date_str.split('-')]
			d = datetime.date(yyyy,mm,dd)
			return d
		else:
			return None
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler,APIHandler):
	'''For uploading obituaries and images
	'''
	
class AdminHandler(BaseHandler):
	'''For the admin page
	'''
