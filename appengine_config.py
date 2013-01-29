from gaesessions import SessionMiddleware 
from google.appengine.ext.appstats import recording
def webapp_add_wsgi_middleware(app): 
	app = SessionMiddleware(app, cookie_key="'8m\x14\x8f\xb0\x80=b[\xebf\xaea\x94%\r\xa3)\xb18\xdd\x85f\xf9Io|\x16\x02\x03\x81\xd1\x92\xbf\x1bq\xcf\x9f\x90\x91p4\x92\x82\t\xbe\xf4~\xd9\xd4+\xd4\xd0\xdaY\x18\xcb\xb5\x93i\x13\x01\xc9\xd9'")
	app = recording.appstats_wsgi_middleware(app)
	return app
