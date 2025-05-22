from javascript import require

jsdom = require('jsdom')

class Sandbox:
    def __init__(self, domain, user_agent, html_code=''):
        self.site_html = html_code
        self.domain = domain
        self.user_agent = user_agent
        
        self.resources = jsdom.ResourceLoader({'userAgent': self.user_agent})
        self.window = jsdom.JSDOM('', {
            'url': self.domain,
            'referrer': self.domain + '/',
            'contentType': 'text/html',
            'includeNodeLocations': True,
            'pretendToBeVisual': True,
            'resources': self.resources,
            'runScripts': 'dangerously',
        }).getInternalVMContext()