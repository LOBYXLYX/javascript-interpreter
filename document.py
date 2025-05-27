import re
from bs4 import BeautifulSoup
    
class NodeType:
    ELEMENT_NODE = 1
    ATTRIBUTE_NODE = 2
    TEXT_NODE = 3
    CDATA_SECTION_NODE = 4
    ENTITY_REFERENCE_NODE = 5
    ENTITY_NODE = 6
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11
    NOTATION_NODE = 12
    
    def __init__(self, node_type=None, node_name=None):
        self.nodeType = node_type
        self.nodeName = node_name
        self.children = []
        self.parentNode = None
    
    def appendChild(self, node):
        node.parentNode = self
        self.childNodes.append(node)
        return node
    
class DOMStringList:
    def __init__(self):
        self.length = 0
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
    
class Location:
    def __init__(self, domain):
        self.ancestorOrigins = DOMStringList()
        self.hash = ''
        self.host = domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.hostName = domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.href = ''
        self.origin = 'https://' + domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.pathname = domain.split('//')[1].split('/', 1)[1]
        
        if domain.count(':') == 2:
            self.port = domain.split('/', 1)[1].split(':')[1].split('/')[0]
        else:
            self.port = ''
        
        self.protocol = domain.split('//')[0]
        self.search = ''
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class Event:
    def __init__(self, type_, options=None):
        options = options or {}
        self.type = type_
        self.bubbles = options.get('bubbles', False)
        self.cancelable = options.get('cancelable', False)
        self.defaultPrevented = False
        self.target = None
        self.currentTarget = None
        self._stopped = False
        
    def preventDefault(self):
        if self.cancelable:
            self.defaultPrevented = True

    def stopPropagation(self):
        self._stopped = True
        
    def __repr__(self):
        return f'<Event type="{self.type}">'
    
class MouseEvent(Event):
    def __init__(self, type_, options=None):
        super().__init__(type_, options)
        options = options or {}
        self.altKey = options.get('altKey', False)
        self.button = options.get('button', 0)
        self.buttons = options.get('buttons', 0)
        self.clientX = options.get('clientX', 0)
        self.clientY = options.get('clientY', 0)
        self.ctrlKey = options.get('ctrlKey', False)
        self.metaKey = options.get('metaKey', False)
        self.movementX = options.get('movementX', 0)
        self.movementY = options.get('movementY', 0)
        self.offsetX = options.get('offsetX', 0)
        self.offsetY = options.get('offsetY', 0)
        self.pageX = options.get('pageX', 0)
        self.pageY = options.get('pageY', 0)
        self.relatedTarget = options.get('relatedTarget', None)
        self.screenX = options.get('screenX', 0)
        self.screenY = options.get('screenY', 0)
        self.shiftKey = options.get('shiftKey', False)
        self.x = options.get('x', self.clientX)
        self.y = options.get('y', self.clientY)
        
    def preventDefault(self):
        if self.cancelable:
            self.defaultPrevented = True

    def stopPropagation(self):
        pass

    def stopImmediatePropagation(self):
        pass

    def __repr__(self):
        return f"<MouseEvent type='{self.type}' client=({self.clientX},{self.clientY})>"
        
class ShadowRoot:
    def __init__(self, host, mode='open'):
        self.host = host
        self.mode = mode
        self.childNodes = []
        
        self.innerHTML = ''
        self.isConnected = True
        self.nodeType = 11
        self.nodeName = '#shadow-root'
    
    def appendChild(self, node):
        node.parentNode = self
        self.childNodes.append(node)
        return node
    
    def querySelector(self, selector):
        for child in self.childNodes:
            if getattr(child, 'matches', lambda _: False)(selector):
                return child
            if hasattr(child, 'querySelector'):
                result = child.querySelector(selector)
                if result:
                    return result
        return None
        
    def toHTML(self):
        return ''.join(child.toHTML() if hasattr(child, 'toHTML') else str(child) for child in self.childNodes)
        
    def __repr__(self):
        return f"<ShadowRoot mode={self.mode} children={len(self.childNodes)}>"

class Element(NodeType):
    def __init__(self, tag_name):
        super().__init__(node_type=1, node_name=tag_name.upper())
        self.tagName = tag_name.upper()
        self.children = []
        self.nodeType = NodeType.ELEMENT_NODE
        self.attributes = {}
        self.id = None
        self.innerHTML = ''
        self.style = {}
        self.parentNode = None
        
        self.classNAme = ''
        self.ownerDocument = None
        self.tabIndex = -1
        self.onfocus = None
        self.onblur = None
        self._event_listeners = {}
        
    @property
    def className(self):
        return self.attributes.get('class', '')
    
    @className.setter
    def className(self, value):
        self.attributes['class'] = value
        
    def attachShadow(self, options):
        mode = options.get('mode', 'open')
        self.shadowRoot = ShadowRoot(host=self, mode=mode)
        return self.shadowRoot
    
    def matches(self, selector):
        if selector.startswith("#"):
            return self.id == selector[1:]
        if selector.startswith("."):
            return selector[1:] in self.className.split()
        return self.tagName == selector.upper()

    def toHTML(self):
        tag = self.tagName.upper()
        attrs = f' class="{self.className}"' if self.className else ''
        children_html = ''.join(child.toHTML() if hasattr(child, 'toHTML') else str(child) for child in self.children)
        shadow_html = self.shadowRoot.toHTML() if self.shadowRoot and self.shadowRoot.mode == 'open' else ''
        content = shadow_html + self.innerHTML + children_html
        return f'<{tag}{attrs}>{content}</{tag}>'
        
    def addEventListener(self, event_type, callback):
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def removeEventListener(self, event_type, callback):
        if event_type in self._event_listeners:
            try:
                self._event_listeners[event_type].remove(callback)
            except ValueError:
                pass

    def dispatchEvent(self, event):
        event.target = self
        event.currentTarget = self
        listeners = self._event_listeners.get(event['type'], [])
        for callback in listeners:
            callback(event)
        return not event.defaultPrevented
        
    def focus(self):
        if self.ownerDocument:
            self.ownerDocument.activeElement = self
            if callable(self.onfocus):
                self.onfocus()
            self.dispatchEvent({'type': 'focus', 'target': self})
    
    def blur(self):
        if self.ownerDocument and self.ownerDocument.activeElement == self:
            self.ownerDocument.activeElement = None
            if callable(self.onblur):
                self.onblur()
            self.dispatchEvent({'type': 'focus', 'target': self})
        
    def setAttribute(self, key, value):
        self.attributes[key] = value
        
        if key == 'class':
            self.className = value
        elif key == 'id':
            self.id = value
        elif key == 'tabIndex':
            try:
                self.tabIndex = int(value)
            except ValueError:
                self.tabIndex = -1
            
    def getAttribute(self, name):
        return self.attributes.get(name, None)
    
    def removeAttribute(self, name):
        self.attributes.pop(name, None)
        
    def querySelector(self, selector):
        if selector.startswith('#'):
            target_id = selector[:1]
            return self._find_by_id(target_id)
        else:
            return self._find_by_tag(selector.upper())
        
    def _find_by_id(self, id_value):
        if self.id == id_value:
            return self
        
        for child in self.children:
            found = child._find_by_id(id_value)
            if found:
                return found
        return
    
    def _find_by_tag(self, tag_name):
        if self.tagName == tag_name:
            return self
        for child in self.children:
            found = child._find_by_tag(tag_name)
            if found:
                return found
        return
    
    def __repr__(self):
        return f"<{self.tagName} class='{self.className}' id='{self.id}'>"
    
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        

class Document(NodeType):
    def __init__(self, window, domain, html='', content_type='text/html'):
        self._html_code = html
        self._soup = BeautifulSoup(self._html_code, 'html.parser')
        super().__init__(node_type=9, node_name='#document')
        
        self.readyState = False
        self.domain = domain
        self.window = window
        self.location = Location(domain)
        self.baseURI = 'https://' + (domain.split('/')[2] if len(domain.split('/')) > 3 else domain) + '/'
        self.contentType = content_type
        self.body = {
            'innerHTML': repr(self._html_code)
        }
        self.children = []
        self._activeElement = None
        self.fullscreen = False
    
    @property
    def activeElement(self):
        return self._activeElement
    
    @activeElement.setter
    def activeElement(self, element):
        self._activeElement = element
    
    @property
    def all(self):
        total_elements = []
        
        def _dfs(node):
            if isinstance(node, Element):
                total_elements.append(node)
            for child in getattr(node, 'children', []):
                _dfs(child)
        _dfs(self)
        return total_elements
        
    def createElement(self, tag_name):
        elem =  Element(tag_name)
        self.children.append(elem)
        self.all.append(elem)
        return elem
    
    def getElementsByName(self, name):
        return [el for el in self.all if el.attributes.get('name') == name]
    
    def getElementsByTagName(self, tag_name):
        results = []

        def traverse(node):
            if hasattr(node, 'tag_name'):
                if tag_name == '*' or node.tag_name.lower() == tag_name.lower():
                    results.append(node)
            if hasattr(node, 'childNodes'):
                for child in node.childNodes:
                    traverse(child)

        traverse(self)
        return results
    
    def getElementById(self, element_id):
        found = None

        def traverse(node):
            nonlocal found
            if getattr(node, 'id', None) == element_id:
                found = node
                return
            if hasattr(node, 'childNodes'):
                for child in node.childNodes:
                    traverse(child)
                    if found:
                        return
        traverse(self)
        return found
    
    def appendChild(self, node):
        if not hasattr(self, '_child_nodes'):
            self._child_nodes = []
        self._child_nodes.append(node)
        node.parentNode = self
    
    def querySelector(self, selector):
        for child in self.children:
            found = child.querySelector(selector)
            
            if found:
                return found
        return
    
    def querySelectorAll(self, selector):
        name_match = re.match(r'\[name=["\'](.+?)["\']\]', selector)
        if name_match:
            name = name_match.group(1)
            return self.getElementsByName(name)
        return []
        
    def __str__(self):
        return repr(self._html_code)
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        

if __name__ == '__main__':
    window = {
        'document': Document({}, 'https://nopecha.com/demo/',open('tests/html_test.html', 'r').read())
    }

    div = window['document'].createElement('div')
    print(div.ELEMENT_NODE)