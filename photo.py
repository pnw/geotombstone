from google.appengine.ext import blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
import handlers
import models
import utils
import webapp2
class ServeImageHandler(blobstore_handlers.BlobstoreDownloadHandler,handlers.BaseHandler):
	def get(self,oid):
		'''
		The phone is requesting an obituary image
		'''
		try:
			photo_id = self.rget('p', int, True)
			photo_key = ndb.Key(models.Obituary,int(oid),models.Photo,photo_id)
			photo = photo_key.get()
			blob_key = photo.img_key
			blob_info = blobstore.BlobInfo(blob_key)
			self.send_blob(blob_info)
		except Exception,e:
			utils.log_error(e)
			return None
app = webapp2.WSGIApplication([
							('/photo/(.*)',ServeImageHandler)
							])