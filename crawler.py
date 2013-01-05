'''
Created on 28/nov/2012

@author: mlarocca


Assumptions:
Only crawls static content
  Anchors
  Imgs
  Scripts
  Stylesheets
  Forms (only those using get method)
Discards query parameters and #fragments
URLs can't contain quotes or double quotes
Relocation and forms submission by javascript are ignored
Doesn't check if tags are well formes, and well placed (f.i. if A and 
    FORM only appears in body section)
Only URLs on the same domain are listed


The crawler is a Breadth-first multithread crawler, keeping a queue of 
the URLs that are encountered.
Main class is CrawlHandler. Once created, crawling can be started on 
any page using start_crawling(url). It is possible to crawl only one site 
at the same time.

It is possible to hand over three extra parameters to start_crawling:
- The number of threads to be started (each thread will pick up elements
  from the common queue and ;
- A limit to the number of pages crawled;
- A delay between two consecutive requests of a single Crawler (to 
  allow for polite crawling, default is 0.15 seconds)

The actual crawling is made by class Crawler: each instance of Crawler runs
in a separate thread.
A list of pages already visited is used to avoid circular
redirection between pages.
'''
from Queue import Queue, Empty
from urllib import urlopen
from urlparse import urlsplit, urlunsplit, urljoin
from time import time, sleep
from sets import Set
import threading

#Logging
from datetime import datetime
import logging
#Regular Expressions
import re

DEFAULT_CRAWLER_DELAY = 1.500  #Polite strategy: at least 1.5 seconds between two pages retrieval

#Waits at most 5 seconds for the queue to get populated
DEFAULT_WAIT = 5

threadLock = threading.Lock()

A_href_regex = re.compile(r'<a.*?href\s*?=\s*?[\'"]([^\'"]*)[\'"]' , re.DOTALL | re.IGNORECASE)
link_href_regex = re.compile(r'<link.*?href\s*?=\s*?[\'"]([^\'"]*)[\'"]' , re.DOTALL | re.IGNORECASE)
script_src_regex = re.compile(r'<script.*?src\s*?=\s*?[\'"]([^\'"]*)[\'"]', re.DOTALL | re.IGNORECASE)
img_src_regex = re.compile(r'<img.*?src\s*?=\s*?[\'"]([^\'"]*)[\'"]', re.DOTALL | re.IGNORECASE)
form_action_regex = re.compile(r'<form.*? method\s*?=\s*?[\'"]get[\'"] action\s*?=\s*?[\'"]([^\'"]*)[\'"]', re.DOTALL | re.IGNORECASE)
comment_regex = re.compile(r'<!--.*?-->' , re.DOTALL | re.IGNORECASE)
                                          
'''  Given a portion of HTML code, extracts all the values for the href attribute of anchor tags
     @param html: the text to parse
'''
def extract_A_href(html):
  return A_href_regex.findall(html)

'''  Given a portion of HTML code, extracts all the values for the href attribute of link tags
     @param html: the text to parse
'''
def extract_link_href(html):
  return link_href_regex.findall(html)

'''  Given a portion of HTML code, extracts all the values for the sec attribute of script tags
     @param html: the text to parse
'''
def extract_script_src(html):
  return script_src_regex.findall(html)

'''  Given a portion of HTML code, extracts all the values for the src attribute of anchor tags
     @param html: the text to parse
'''
def extract_img_src(html):
  return img_src_regex.findall(html)

'''  Given a portion of HTML code, extracts all the values for the href attribute of anchor tags
     @param html: the text to parse
'''
def extract_form_action(html):
  return form_action_regex.findall(html)

'''  Given a portion of HTML code, returns the html obtained by stripping all the HTML comments
     @param html: the text to parse
'''
def strip_comments(html):  
  return comment_regex.sub("", html)
  
  
'''Data structure to represent a page
  Separate fields keeps track of all the static content linked from the page (see above)
'''
class Page(object):
  
  def __init__(self, url, handler):
    # Get lock to synchronize threads
    threadLock.acquire(True)    
    self.page_ID = handler.page_index
    handler.page_index += 1
    # Free lock to release next thread
    threadLock.release()    
          
    _, self.domain, self.path, _, _ = urlsplit(url)
    self.links = Set()
    self.css_urls = Set()
    self.script_urls = Set()
    self.img_urls = Set()
    self.__handler = handler
    self.__retrieve(url)

  
  def __retrieve(self, url):
    logging.info("Crawling page: %s; time:%s\n" % (url, datetime.now())) #Logs current page in order to give signals of its activity
    try:
      page = urlopen(url)
    except: #pragma: no cover
      logging.error("Error: can't open %s" % url)
      return {}
    try:  
      html = "\n".join(page.readlines())
    except KeyError:  #pragma: no cover
      logging.error("Error")
      return None
      
    logging.debug("successfully crawled")
    
    html = strip_comments(html)
    
    links_found = Set(extract_A_href(html)).union(extract_form_action(html))
    self.img_urls = Set(extract_img_src(html))
    self.script_urls = Set(extract_script_src(html))
    self.css_urls = Set(extract_link_href(html))
    
    for link_url in links_found:
      self.enqueue_link(link_url)

#DEBUG
    logging.debug(str(self.links))
    logging.debug(str(self.img_urls))
    logging.debug(str(self.script_urls))
    logging.debug(str(self.css_urls))
    
  ''' Gets the link properly formatted.
      
      If the URL belongs to another domain, it is neglected;
      If it belongs to this domain, may or may not have been added to the queue
      (it's note this page's responsability); however, it will be linked from this page)
  '''
  def enqueue_link(self, url):
    page_url = self.__handler.format_and_enqueue_url(url, self.path)
    if page_url is None:
      return  #pragma: no cover
    else:
      self.links.add(page_url)
      


'''An actual breadth-first crawler
'''
class Crawler(threading.Thread):
#Multithread      #MAX_TIMEOUT = 10 * crawler_delay    #Max time to wait for the queue to get populated (after that, returns)
  
  def __init__(self, threadID, handler):
    self.threadID = threadID
    self.__handler = handler
    threading.Thread.__init__(self)
    
  def run(self):
    self.crawl_next()
      
  #Breadth-first crawling
  def crawl_next(self):
    
    #Crawls at most one page every crawler_delay ms
    sleep( min(time() - self.__handler.last_crawl_time, self.__handler.crawler_delay))

    #Updates crawl time 
    self.__handler.last_crawl_time = time()
     
    try:
      page_url = self.__handler.queue.get(True, DEFAULT_WAIT)
    
    except Empty:
      logging.info("Thread %d releasing" % self.threadID)
      return
    
    logging.info("Thread %d crawling %s" % (self.threadID, page_url))
    page = Page(page_url, self.__handler)
    
    #Updates last crawl time 
    self.__handler.last_crawl_time = time()
    
    self.__handler.site[page.page_ID] = page
    self.__handler.url_to_page_id[page_url] = page.page_ID
    self.__handler.queue.task_done()

    return self.crawl_next()
  
class CrawlerHandler(object):
  
  def __init__(self):
    self.page_index = 0
     
  '''Enqueue a url to a page to be retrieved, if it hasn't been enqueued yet
     and if it is "valid", meaning it's in the same domain as the main page
     @page_url: the original URL to be enqueued
     @current_path: the path of current page (for relative URLs)
     @return: None <=> the URL is located in a different domain
              The formatted absolute URL, otherwise
  '''
  def format_and_enqueue_url(self, page_url, current_path):  
    (scheme, domain, path, _, _) = urlsplit(page_url)
    if scheme == '':
      scheme = self.__home_scheme
#      elif scheme == 'https':
#        scheme = 'http'
    if domain == '':
      domain = self.__home_domain
      path = urljoin(current_path, path)
    elif domain != self.__home_domain or ( scheme != self.__home_scheme):
      return None  
    #The page can be  
    page_url = urlunsplit((scheme, domain, path, '', '')) #discards query and fragment
    if (not page_url is '' and not page_url in self.__queued_pages_urls
        and (self.__max_pages_to_crawl is None or len(self.__queued_pages_urls) <self.__max_pages_to_crawl)):
      self.queue.put(page_url) #Common access to the containing class queue  for all Crawler instances
      self.__queued_pages_urls[page_url] = True    #marks the url as visited
      return page_url
   
    return page_url
              
  def start_crawling(self, url, threads = 1, max_pages_to_crawl = None, crawler_delay = DEFAULT_CRAWLER_DELAY):

    self.last_crawl_time = 0
    self.queue = Queue()
    self.__queued_pages_urls = {}  #Keeps track of the pages already crawled, to avoid deadlock and endless circles
    self.__max_pages_to_crawl = max_pages_to_crawl
    self.crawler_delay = crawler_delay
    self.page_index = 0
    self.site = {}   #Map pages' ID to the real objects
    self.url_to_page_id = {} #Map URLs to page IDs   
    self.queue = Queue()
    
    (self.__home_scheme, self.__home_domain, _, _ , _) = urlsplit(url)
 
    #Might be necessary if distinctions among protocols are considered
#    if home_scheme == 'https':
#      home_scheme = 'http'

    home_page_url = self.format_and_enqueue_url(url, '')
  
    for i in xrange(threads):
      crawler = Crawler(i, self)
      crawler.daemon = True 
      crawler.start()
    
    self.queue.join()
      
    return home_page_url


  '''Starting from the home page, lists all the resources used 
     by in it and in all the pages on the same domain reachable from the home page
  '''  
  def list_resources(self, home_page_url):
    
    pages_visited = {}
    
    '''Recursively lists all the resources used by the current page and all the linked pages
    '''
    def recursive_list(page, img_set, css_set, script_set):
      try:
        img_set = img_set | page.img_urls
        css_set = css_set | page.css_urls
        script_set = script_set | page.script_urls
      except: #pragma: no cover
        return img_set, css_set, script_set
      
      try:
        for link_url in page.links:
          link_page_id = self.url_to_page_id[link_url]
          if not link_page_id in pages_visited:
            pages_visited[link_page_id] = True
            img_set, css_set, script_set = recursive_list(self.site[link_page_id], img_set, css_set, script_set)
      except KeyError:
        pass
    
      return img_set, css_set, script_set
      
    img_set, css_set, script_set = recursive_list(self.site[self.url_to_page_id[home_page_url]], Set(), Set(), Set())
    return {"images": img_set, "css": css_set, "scripts": script_set}
  