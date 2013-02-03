import webapp2
import handlers
import jinja2
import os
import models
import logging
from google.appengine.ext import ndb
import utils
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from gaesessions import get_current_session
from google.appengine.api import users as google_users
import json
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
class LandingHandler(handlers.WebHandler):
	def get(self):
		'''
		The landing page of the app - full screen map
		'''
		session = get_current_session()
		user = self.get_user_from_session(session)
		logged_in = True if user else False
		
		
		# needed for redirect on login page
		if not logged_in:
			session['last_page'] = self.request.url
		
		
		# grab the lat, lon from the headers
		try:
			geo_point = self.request.headers['X-Appengine-Citylatlong']
		except KeyError:
			# default to boston
			geo_point = '42.3584308,-71.0597732'
			# default to san fransisco
#			geo_point = '37.7749295,-122.4194155'
		lat,lon = geo_point.split(',')
		lat = float(lat)
		lon = float(lon)
		
		uastring = str(self.request.headers['user-agent'])
	
		logging.info(uastring)
			
		if 'mobile' in uastring.lower():
			desktop = False
		else:
			desktop = True
		
		desktop_param = self.request.get("desktop","notfound")
		
		if desktop_param != "notfound":
			desktop = desktop_param
			
		logging.info(desktop)
		
		template_values = {
						'logged_in' : logged_in,
						'admin' : google_users.is_current_user_admin(),
						'lat' : lat,
						'lon' : lon,
						'desktop' :	desktop
						}
		
		template = jinja_environment.get_template('templates/landing.html')
		self.response.out.write(template.render(template_values))
class SearchHandler(handlers.WebHandler):
	def get(self):
		'''
		Ajax call to search for obituaries
		'''
		try:
			obits = self.full_search()
			# only take top 50 matched obits
			obits = list(obits)[:75]
			
			
			user = self.get_user_from_session()
			response = {
					'results' : [o.package(web=True) for o in obits],
					'logged_in' : True if user else False
					}
		except self.InputError,e:
			utils.log_error(e)
			logging.info('input error')
			key = e.message.split(':')[0]
			return self.send_response(400,e.message,{'invalid_input':key})
		except Exception,e:
			utils.log_error(e)
			logging.info('exception')
			return self.send_server_error(e.message)
		else:
			return self.send_success(response)
class ObituaryPageHandler(handlers.WebHandler):
	def get(self,oid):
		'''
		Page to display detail about a deceased person
		'''
		# determine user state
		session = get_current_session()
		user = self.get_user_from_session(session)
		logged_in = True if user else False
		admin = google_users.is_current_user_admin()
		# needed for redirect on login page
		if not logged_in:
			session['last_page'] = self.request.url
		
		# grab the obituary
		obit = self.get_by_id(models.Obituary,oid)
		
		# get messages and narratives
		message_keys = models.Message.query(ancestor = obit.key).iter(keys_only=True)
		message_futures = ndb.get_multi_async(message_keys)
		narrative_keys = models.Narrative.query(ancestor = obit.key).iter(keys_only=True)
		narrative_futures = ndb.get_multi_async(narrative_keys)
		messages = (f.get_result() for f in message_futures)
		narratives = (f.get_result() for f in narrative_futures)
		
		# base url for posting changes
		base_url = '/obituary/{}'.format(obit.key.id())
		upload_photo_url = blobstore.create_upload_url('{}/add_photo'.format(base_url))
		
		template_values = {
						# data variables
						'obituary' : obit,
						'messages' : messages,
						'narratives' : narratives,
						# update entity variables
						'edit_data_url' : base_url,
						'add_message_url' : base_url+'/add_message',
						'add_narrative_url' : base_url+'/add_narrative',
						'upload_photo_url' : upload_photo_url,
						# state variables
						'logged_in' : logged_in,
						'admin' : admin,
						'editable' : admin or logged_in # true if logged in or admin
						}
		
#		self.response.out.write(template_values)
#		self.response.out.write(obit.get_photo_urls())
		template = jinja_environment.get_template('templates/obituary_page.html')
		self.response.out.write(template.render(template_values))
	def post(self,oid):
		'''
		Logged in person can edit the obituary info
		'''
		user = self.get_user_from_session()
		if not user:
			return self.redirect('/')
		
		try:
			obit = self.get_by_id(models.Obituary, oid)
			assert obit, 'Invalid oid'
			
			# dates
			dob = self.rget('dob',self.parse_date)
			if dob:
				obit.dob = dob
			dod = self.rget('dod',self.parse_date)
			if dod:
				obit.dod = dod
			# birth/death locations
			pob = self.rget('pob',str)
			if pob:
				obit.pob = pob
			pod = self.rget('pod',str)
			if pod:
				obit.pod = pod
			
			# other
			name = self.rget('name',str,True)
			if name:
				obit.name = name
			tombstone_message = self.rget('tombstone_message',str) or None
			logging.info('\n\n')
			logging.info(tombstone_message)
			if tombstone_message:
				obit.tombstone_message = tombstone_message
			
			logging.info(obit.to_dict())
			# replace the modified obituary
			ndb.transaction(lambda: obit.put())
		except Exception,e:
			logging.info(e.message)
		finally:
			return self.redirect(self.request.referrer)
class AddPhotoHandler(blobstore_handlers.BlobstoreUploadHandler,handlers.WebHandler):
	def post(self,oid):
		'''
		A user is uploading another image for the obituary page
		'''
		try:
			obit = self.get_by_id(models.Obituary, oid)
			assert obit, 'Invalid oid: {}'.format(oid)
			
			# fetch the uploaded image(s)
			img_keys = [p.key() for p in self.get_uploads()]
			# create images
			for key in img_keys:
				self.create_entity(
								# model, parent
								models.Photo, obit.key,
								# params
								img_key=key)
			
		except Exception,e:
			utils.log_error(e)
			
		finally:
			return self.redirect(self.request.referrer)
		
	
class AddMessageHandler(handlers.WebHandler):
	def post(self,oid):
		'''
		A user is adding a message to loved ones
		'''
		try:
			obit = self.get_by_id(models.Obituary, oid)
			assert obit, 'Invalid oid: {}'.format(oid)
			author = self.get_user_from_session()
			# message details
			author_name = self.rget('author_name',str)
			message = self.rget('message',str,True)
			# create the message
			self.create_entity(
							models.Message,
							obit.key,
							author_key = author.key if author else None,
							message = message,
							author_name = author_name
							)
		except Exception,e:
			utils.log_error(e)
		finally:
			# redirect back to obit page
			return self.redirect(self.request.referrer)
class AddNarrativeHandler(handlers.WebHandler):
	def post(self,oid):
		'''
		A user is adding a message about the deceased
		'''
		try:
			obit = self.get_by_id(models.Obituary, oid)
			assert obit, 'Invalid oid: {}'.format(oid)
			author = self.get_user_from_session()
			# message details
			author_name = self.rget('author_name',str)
			message = self.rget('message',str,True)
			# create the message
			self.create_entity(
							models.Narrative,
							obit.key,
							author_key = author.key if author else None,
							message = message,
							author_name = author_name
							)
			
		finally:
			# redirect back to obit page
			return self.redirect(self.request.referrer)
class LoginHandler(handlers.WebHandler):
	def get(self):
		'''Login page. No more, no less.
		'''
		template_values = {
						'error' : self.rget('error',bool),
						'post_url' : self.request.url,
						'admin' : google_users.is_current_user_admin()
						}
		template = jinja_environment.get_template('templates/log_in.html')
		self.response.out.write(template.render(template_values))
	def post(self):
		'''
		User logs in via ajax
		'''
		try:
			email = self.rget('email',str,True)
			
			# grab an existing user and check if pw matches the stored pw
			user = models.WebUser.query(models.WebUser.email == email).get()
			
			user_salt = user.pw.salt
			existing_hashed_pw = user.pw.pw
			input_pw = self.rget('pw',str,True)
			input_hashed_pw,_ = self.hash_password(input_pw, user_salt)
			assert existing_hashed_pw == input_hashed_pw, 'Invalid email password combination'
			
			# log user in
			uid = user.key.id()
			
		except Exception,e:
			utils.log_error(e)
			ref = self.request.referrer.split('?')[0]
			new_url = '{}?error=true'.format(ref)
			return self.redirect(new_url)
		else:
			session = self.log_in(uid)
			try:
				# redirect to the last page that was visited
				return self.redirect(session['last_page'])
			except KeyError:
				return self.redirect('/')
			
class LogoutHandler(handlers.WebHandler):
	def get(self):
		'''
		User logs out
		'''
		self.log_out()
		return self.redirect(self.request.referrer)
class CreateAccountHandler(handlers.WebHandler):
	def get(self):
		'''Create account page. No more, no less.
		'''
		template_values = {
						'error' : self.rget('error',str),
						'post_url' : self.request.url,
						'admin' : google_users.is_current_user_admin()
						}
		template = jinja_environment.get_template('templates/sign_up.html')
		self.response.out.write(template.render(template_values))
		
	def post(self):
		'''
		Create a new web account via ajax call
		'''
		class EmailExists(Exception):
			'''Email already exists'''
		class PWDontMatch(Exception):
			'''Passwords dont match'''
		class PWLength(Exception):
			'''Passwords must be at least 6 characters'''
		try:
			email = self.rget('email',str,True)
			pw = self.rget('pw',str,True)
			pw_2 = self.rget('pw_2',str,True)
			if pw != pw_2:
				raise PWDontMatch
			elif len(pw) < 6:
				raise PWLength
			existing_user = models.WebUser.query(models.WebUser.email == email).get()
			if existing_user is not None:
				raise EmailExists
			
			# create the user
			user = self.create_web_user(email,pw)
			
			# log user in
			uid = user.key.id()
			session = self.log_in(uid)
		except PWDontMatch:
			ref = self.request.referrer.split('?')[0]
			new_url = '{}?error=pw'.format(ref)
			return self.redirect(new_url)
		except EmailExists:
			ref = self.request.referrer.split('?')[0]
			new_url = '{}?error=email'.format(ref)
			return self.redirect(new_url)
		except PWLength:
			ref = self.request.referrer.split('?')[0]
			new_url = '{}?error=length'.format(ref)
			return self.redirect(new_url)
#		except self.InputError,e:
#			ref = self.request.referrer.split('?')[0]
#			key = e.message.split(':')[0]
#			new_url = '{}?error=missing&field='.format(ref,key)
#			return self.redirect(new_url)
		else:
			try:
				# redirect to the last page that was visited
				return self.redirect(session['last_page'])
			except KeyError:
				return self.redirect('/')
app = webapp2.WSGIApplication([
							('/search',SearchHandler),
							('/obituary/(.*)/add_narrative',AddNarrativeHandler),
							('/obituary/(.*)/add_message',AddMessageHandler),
							('/obituary/(.*)/add_photo',AddPhotoHandler),
							('/obituary/(.*)',ObituaryPageHandler),
							('/log_in',LoginHandler),
							('/log_out',LogoutHandler),
							('/create_account',CreateAccountHandler),
							('/',LandingHandler),
							])