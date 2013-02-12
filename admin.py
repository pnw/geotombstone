from google.appengine.ext import ndb
import handlers
import jinja2
import models
import os
import utils
import webapp2
import logging
from gaesessions import get_current_session
from google.appengine.ext import blobstore
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
class ViewUsersHandler(handlers.AdminHandler):
	def get(self):
		'''
		Page to view all users and possibly delete them
		'''
		session = get_current_session()
		try:
			uid = session['uid']
		except KeyError:
			user = None
		else:
			user = models.WebUser.get_by_id(uid)
		logged_in = True if user is not None else False
		
		# get all user accounts
		user_keys = models.WebUser.query().order(models.WebUser.email).iter(keys_only=True)
		user_futures = ndb.get_multi_async(user_keys)
		users = (f.get_result() for f in user_futures)
		
		packaged_users = [
						{
						'email':user.email,
						'delete_url':'{}/admin/users/{}/delete'.format(utils.BASE_URL,user.key.id())
						} for user in users]
		
		
		template_values = {
						'users' : packaged_users,
						'logged_in' : logged_in
						}
		template = jinja_environment.get_template('templates/admin/manage_users.html')
		self.response.out.write(template.render(template_values))
		
class DeleteWebUserHandler(handlers.AdminHandler):
	def post(self,uid):
		'''Delete a user
		'''
		uid = int(uid)
		assert uid, 'uid required'
		user_key = ndb.Key(models.WebUser,uid)
		user_key.delete()
		return self.redirect(self.request.referrer)
		
class DeleteObituaryHandler(handlers.AdminHandler):
	def post(self,oid):
		'''Delete an obituary
		'''
		oid = int(oid)
		assert oid, 'oid required'
		results = []
		# create key for the obituary
#		obit_key = ndb.Key(models.Obituary,oid)
		obit = models.Obituary.get_by_id(oid)
		# find all references to the obituary and delete them too
		bookmark_keys = models.Bookmark.query(models.Bookmark.obit_key == obit.key).iter(keys_only=True)
		results.extend(ndb.delete_multi_async(bookmark_keys))
		
		results.extend(ndb.delete_multi_async(obit.narrative_keys))
		
		results.extend(ndb.delete_multi_async(obit.message_keys))
		
		# grab the attached photo references and delete them along with the referenced blob keys
		photos = obit.photos
		logging.info(type(photos))
		blob_keys = []
		photo_keys = []
		for photo in photos:
			logging.info(photo)
			blob_keys.append(photo.img_key)
			photo_keys.append(photo.key)
		# delete the photo entities
		results.extend(ndb.delete_multi_async(photo_keys))
		# delete the blobs
		blobstore.delete(blob_keys)
		# delete the obit
		obit.key.delete()
		
		# get all the results
		r = [f.get_result() for f in results]
app = webapp2.WSGIApplication([
							('/admin/users',ViewUsersHandler),
							('/admin/users/(.*)/delete',DeleteWebUserHandler),
							('/admin/obituaries/(.*)/delete',DeleteObituaryHandler)
							])