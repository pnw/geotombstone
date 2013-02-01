import webapp2
import handlers
import utils as u
import models
from google.appengine.ext import ndb
from geo import geohash
import logging
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore


class CreateUserHandler(handlers.APIHandler):
	def get(self):
		upload_url = '/api/create_user'
		self.response.out.write('<html><body>')
		self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
		self.response.out.write("""
			<input type="text" name="name" value="Patrick Walsh">
			<input type="text" name="email" value="patrick@levr.com">
			<input type="text" name="phone" value="111-445-6674">
			<input type="text" name="address" value="260 Everett St">
			<input type="submit" name="submit" value="Submit">
			""")
	def post(self):
		'''
		A user account is being created on the phone
		'''
		try:
			user = self.create_entity(models.AppUser,
								name = self.rget('name',str,True),
								email = self.rget('email',str,True),
								phone = self.rget('phone',str) or None,
								address = self.rget('address',str) or None,
								)
			response = {
					'uid' : user.key.id()
					}
		except self.InputError,e:
			key = e.message.split(':')[0]
			return self.send_response(400,e.message,{'invalid_input':key})
		else:
			return self.send_success(response)
			
class UploadObituaryHandler(handlers.UploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/api/create_geotag')
		self.response.out.write('<html><body>')
		self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
		self.response.out.write("""Upload File: <input type="file" name="file"><br>
			<input type="text" name="lat" value="42.3432">
			<input type="text" name="lon" value="-72.13213">
			<input type="text" name="dob" value="1990-03-03">
			<input type="text" name="dod" value="2070-01-10">
			<input type="text" name="name" value="Patrick Walsh">
			<input type="text" name="pob" value="Salem, NH">
			<input type="text" name="pod" value="Rockingham County">
			<input type="text" name="uploader_id" value="106">
			<input type="submit" name="submit" value="Submit">
			""")
		
		self.response.out.write("""</form></body></html>""")
	def post(self):
		'''
		A user is geotagging a tombstone
		'''
		# get the blobstore key of the image if an image is uploaded
		try:
			logging.info(self.request)
			logging.info(self.request.headers)
			logging.info(self.request.params)
			# tombstone location
			lat = self.rget('lat',float,True)
			lon = self.rget('lon',float,True)
			ghash = geohash.encode(lat,lon)
			
			# dates
			dob = self.rget('dob',self.parse_date)
			dod = self.rget('dod',self.parse_date)
			# birth/death locations
			pob = self.rget('pob',str)
			pod = self.rget('pod',str)
			
			# other
			name = self.rget('name',str)
			tombstone_message = self.rget('tombstone_message',str) or None
			uploader_id = self.rget('uploader_id',int,True)
			
			# image
			logging.info(self.get_uploads())
			logging.info(self.get_uploads('image'))
			img_keys = [p.key() for p in self.get_uploads()]
			
			# make sure at least one field is entered
			assert dob or dod or pob or pod \
				or name or tombstone_message or img_keys, \
				'Must provide at least one identifying piece of information'
			
			ob = self.create_obituary(
									uploader_key = ndb.Key(models.AppUser,uploader_id),
									name = name,
									ghash = ghash,
									dob = dob,
									dod = dod,
									pob = pob,
									pod = pod,
									tombstone_message = tombstone_message,
									img_keys = img_keys
									)
			
			response = {
					'oid' : ob.key.id(),
					'img_url' : ob.get_photo_urls()
					}
		except AssertionError,e:
			return self.send_response(400,e.message,{'invalid_input':''})
		except self.InputError,e:
			key = e.message.split(':')[0]
			return self.send_response(400,e.message,{'invalid_input':key})
		except Exception,e:
			return self.send_server_error(e.message)
		else:
			return self.send_success(response)
class SearchHandler(handlers.APIHandler):
	def get(self):
		'''
		Someone is searching on the app
		'''
		logging.info('\n\n\n hi')
		try:
			obits = self.full_search()
			# only take top 50 matched obits
			obits = list(obits)[:50]
			
			# fetch the uploader info to attach to the obits
			uploaders = models.Obituary.fetch_author_multi(obits)
			# fetch the messages to attach to the obits
			messages_lists = models.Obituary.fetch_messages_multi(obits)
			# fetch narratives
			narratives_lists = models.Obituary.fetch_narratives_multi(obits)
			
			# package everything
			packaged_uploaders = [u.package() for u in uploaders]
			packaged_messages = [[m.package() for m in messages] for messages in messages_lists]
			packaged_narratives = [[n.package() for n in narratives] for narratives in narratives_lists]
			
			packaged_obituaries = [
								ob.package(
										uploader = packaged_uploaders[idx],
										messages = packaged_messages[idx],
										narratives = packaged_narratives[idx]
										)
								for idx,ob in enumerate(obits)
								]
			
			# package results
			response = {
					'results' : packaged_obituaries,
					}
		except self.InputError,e:
			key = e.message.split(':')[0]
			return self.send_response(400,e.message,{'invalid_input':key})
		except Exception,e:
			return self.send_server_error(e.message)
		else:
			return self.send_success(response)

class FetchUploadURLHandler(handlers.APIHandler):
	def get(self):
		'''
		Phone is requesting an upload url
		'''
		upload_url = blobstore.create_upload_url('/api/create_geotag')
		response = {
				'upload_url' : upload_url
				}
		return self.send_success(response)
class APITestHandler(handlers.APIHandler):
	def get(self):
		'''
		
		'''
		o = models.Obituary.query().get()
		self.say(o.tags)
app = webapp2.WSGIApplication([
							('/api/create_user',CreateUserHandler),
							('/api/create_geotag',UploadObituaryHandler),
							('/api/search',SearchHandler),
							('/api/fetch_upload_url',FetchUploadURLHandler),
#							('/api/test',APITestHandler)
							])
