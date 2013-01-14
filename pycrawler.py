#!/usr/bin/env python

'''
  Created on 28/nov/2012

   PyCrawler is a Breadth-first multithread crawler, keeping a queue of 
   the URLs that are encountered.
   Main class is CrawlHandler. Once created, crawling can be started on 
   any page using start_crawling(url). It is possible to crawl only one site 
   at the same time.
   
   It is possible to hand over three extra parameters to start_crawling:
    * The number of threads to be started (each thread will pick up links
      from a shared synchronized queue and process them);
    * A limit to the number of pages crawled;
    * A delay between two consecutive requests of a single Crawler (to 
      allow for polite crawling, default is 0.15 seconds)

   The actual crawling is made by class Crawler: each instance of Crawler runs
   in a separate thread.
   A list of pages already visited is used to avoid circular
   redirection between pages.
   
   **Assumptions**:
   Only crawls static content
     * Anchors
     * Imgs
     * Scripts
     * Stylesheets
     * Forms (only those using get method)
   Discards query parameters and #fragments
   URLs can't contain quotes or double quotes
   Relocation and forms submission by javascript are ignored
   Doesn't check if tags are well formes, and well placed (f.i. if A and 
       FORM only appears in body section)
   Only URLs on the same domain are listed  
'''


from time import time, sleep
from sets import Set

from HTMLParser import HTMLParser
from urllib2 import urlopen, URLError
from urlparse import urlsplit, urlunsplit, urljoin

#Threads
from Queue import Queue     #, Empty
import threading
import thread
#Logging
from datetime import datetime
import logging


DEFAULT_CRAWLER_DELAY = 1.500  #Polite strategy: at least 1.5 seconds between two pages retrieval

threadLock = threading.Lock()


class PageParser(HTMLParser):
  '''Parses html code into a structured page with separate lists of links to resources and referenced pages.
     
     The constructor creates a parser object and connects it to the page
     
    :param page: A reference to the page object that will hold the structured info for the parsed html page.

  '''  

  def __init__(self, page):  
    self.__page = page

    HTMLParser.__init__(self)
  

  def __retrieve(self, url):
    ''' 
       Try to retrieve a page from its URL.
       :private:
       
       :param url: The URL of the page to be crawled
       
       :return: A string containing the URL of the page to be retrieved
    '''    
    
    logging.info("Crawling page: %s; time:%s\n" % (url, datetime.now())) #Logs current page in order to give signals of its activity
    try:
      page = urlopen(url)
    except URLError:
      logging.error("Error: can't open %s" % url)
      return ""
    try:  
      return "\n".join(page.readlines())
    except KeyError:  #pragma: no cover
      logging.error("Error")
      return None
  
  def startParsing(self, url):
    ''' Retrieve and parses the page located at the specific URL
        
        :param url:  The URL of the page to be retrieved and parsed.
    '''
    html = self.__retrieve(url)
    self.feed(html)
  
  def handle_starttag(self, tag, attrs):
    def unzip(list_of_tuples):
      try:
        return {name: value  for (name, value) in list_of_tuples}
      except: #pragma: no cover
        logging.warning("Invalid Argument for unzip: " + repr(list_of_tuples))
        return {}
      
    tag = tag.lower()
    if tag == 'a':
      attrs = unzip(attrs)
      href = attrs.get('href')
      if href:
        self.__page._links_found.add(href)
    elif tag == 'link':
      attrs = unzip(attrs)
      href = attrs.get('href')
      if href != None:
        self.__page._css_urls.add(href)  
    elif tag == 'form':
      attrs = unzip(attrs)
      action = attrs.get('action')
      if action and attrs.get("method") == "get": #Won't follow post, update or delete actions to avoid causing damage!
        self.__page._links_found.add(action)
    elif tag == 'script':
      attrs = unzip(attrs)
      src = attrs.get('src')
      if src != None:
        self.__page._script_urls.add(src)
    elif tag == 'img':
      attrs = unzip(attrs)
      src = attrs.get('src')
      if src:
        self.__page._img_urls.add(src)
    
    

class Page(object):
  ''' 
    Data structure to represent a page-
    
    Several different fields keeps track of all the static content linked from the page (see project description)
    
    :param url: The URL of the page to page to be hereby retrieved, parsed and stored.
    
    :param handler: A reference to the CrawlerHandler object coordinating the crawling, used to access 
    its format_and_enqueue_url method to add the links found on the current page to the crawler's queue.
  '''   
  
  def __init__(self, url, handler):
    # Get lock to synchronize threads
    threadLock.acquire(True)    
    self.page_ID = handler._page_index
    handler._page_index += 1
    # Free lock to release next thread
    threadLock.release()    
          
    _, self.domain, self.path, _, _ = urlsplit(url)
    self._links = Set()
    self._links_found = Set()
    self._css_urls = Set()
    self._script_urls = Set()
    self._img_urls = Set()
    self.__handler = handler
    self._depth = handler._url_depth[url]
    self._url = url
    
    parser = PageParser(self)
    parser.startParsing(url)
    
    for link_url in self._links_found:
      self.enqueue_link(link_url)

#DEBUG
    logging.debug(str(self._links))
    logging.debug(str(self._img_urls))
    logging.debug(str(self._script_urls))
    logging.debug(str(self._css_urls))
    
    

  def enqueue_link(self, url):
    ''' Takes a link, properly format it, and then keeps track of it for future crawling.
        
        If the URL belongs to another domain, it is neglected (see CrawlerHandler.format_and_enqueue_url specifications)
        If it belongs to this domain, it may or may not have been added to the queue
        (it's note this page's responsability); however, it will be linked from this page)
        
        :param url: The URL to be enqueued.
    '''
    
    page_url = self.__handler.format_and_enqueue_url(url, self.path, self._depth + 1)
    if page_url is None:
      return  #pragma: no cover
    else:
      self._links.add(page_url)      



class Crawler(threading.Thread):
  ''' A breadth-first crawler.
      
      Each crawler object can be run in a separate thread, and access the same synchronized Queue
      to find the next pages to crawl and to enqueue the URLs of the next pages to be crawled.
      
      :param threadID: The ID of the thread in which the crawler is going to be run.
      
      :param handler: A reference to the CrawlerHandler object coordinating the crawling.
  '''
    
  def __init__(self, threadID, handler):
    self.__threadID = threadID
    self.__handler = handler
    threading.Thread.__init__(self)
    
  def run(self):
    ''' Starts the crawler.
    '''

    return self.__crawl_next()  #pragma: no cover (recursive thread call not traced)
    
  def quit(self):
    '''Force the thread to exit.
    
       :raise SystemExit: Always raises a SystemExit to be sure to silently kill the thread: must be caught or the main program will exit as well
    '''
    if self.is_alive():
      self._Thread__stop()
      thread.exit()
  
  def __crawl_next(self):
    ''' Takes the next URL from the queue (if any, otherwise it waits until one is available)
        and tries crawl the resource pointed to. 
        
        :private:
    '''
    #Crawls at most one page every crawler_delay ms
    sleep( min(time() - self.__handler._last_crawl_time, self.__handler._crawler_delay))

    #Updates crawl time 
    self.__handler._last_crawl_time = time()
    
    page_url = self.__handler._queue.get(True) #Wait until an element is available for removal from the queue

#    try:
#      page_url = self.__handler._queue.get()
#    except Empty:
#      logging.info("Thread %d releasing" % self.__threadID)
#      return
    
    logging.debug("Thread %d crawling %s" % (self.__threadID, page_url))
    page = Page(page_url, self.__handler)
    
    #Updates last crawl time 
    self.__handler._last_crawl_time = time()
    
    self.__handler._site[page.page_ID] = page
    self.__handler._url_to_page_id[page_url] = page.page_ID
    self.__handler._queue.task_done()

    return self.__crawl_next() #pragma: no cover (recursive thread call not traced)

    
  
class CrawlerHandler(object):
  ''' The main crawler, the object handling all the high-level crawling process. 
  '''
  
  def __init__(self):
    self._page_index = 0

  def format_and_enqueue_url(self, page_url, current_path, current_depth):       
    ''' Enqueue a url to a page to be retrieved, if it hasn't been enqueued yet
        and if it is "valid", meaning it's in the same domain as the main page
        
        :param page_url: the original URL to be enqueued
        
        :param current_path: the path of current page (for relative URLs)
        
        :param current_depth: depth of the current page (distance from the starting page)
        
        :return:
          -  None <=> the URL is located in a different domain
          -  The formatted absolute URL, otherwise
    '''    
    
    (scheme, domain, path, _, _) = urlsplit(page_url)
    if scheme == '':
      scheme = self.__home_scheme
    elif scheme != self.__home_scheme and not ((scheme == "http" and self.__home_scheme == "https") or (scheme == "https" and self.__home_scheme == "http")):
      return None
#      elif scheme == 'https':
#        scheme = 'http'
    if domain == '':
      domain = self.__home_domain
      path = urljoin(current_path, path)
    elif domain != self.__home_domain or ( scheme != self.__home_scheme):
      return None  
    #The page can be  
    page_url = urlunsplit((scheme, domain, path, '', '')) #discards query and fragment
    #Removes trailing slash
    if page_url[-1] == "/":
      page_url = page_url[:-1]

    if page_url in self._url_depth:
        current_depth = self._url_depth[page_url] = min(self._url_depth[page_url], current_depth)
    else:
        self._url_depth[page_url] = current_depth

    # Get lock to synchronize threads
    threadLock.acquire(True) 
        
    if (page_url != '' and not page_url in self.__queued_pages_urls
        and (self.__max_pages_to_crawl is None or len(self.__queued_pages_urls) < self.__max_pages_to_crawl)
        and (self._max_page_depth is None or current_depth <= self._max_page_depth) ):           
      
      self._queue.put(page_url) #Common access to the containing class queue  for all Crawler instances
      self.__queued_pages_urls[page_url] = True    #marks the url as visited
      
      # Free lock to release next thread
      threadLock.release()  
      
      return page_url
    else:
      # Free lock to release next thread
      threadLock.release()
        
    return page_url
              
  def start_crawling(self, url, threads = 1, max_page_depth = None, max_pages_to_crawl = None, crawler_delay = DEFAULT_CRAWLER_DELAY):
    ''' Starts crawling a website beginning from an URL. 
        Only pages within the same domain will considered for crawling, while pages outside it will be listed among the references of the single pages.
        
        :param url: The starting point for the crawling.
        
        :param threads: Number of concurrent crawlers to be run in separate threads; Must be a positive integer (if omitted or invalid it will be set to 1 by default)
        :type threads: integer or 1

        :param max_page_depth: The maximum depth that can be reached during crawling (if omitted, crawling will stop only  
        when all the pages (or _max_pages_to_crawl_ pages, if it's set) of the same domain reachable from the starting one will be crawled).
        :type max_page_depth: integer or None
        
        :param max_pages_to_crawl: The maximum number of pages to retrieve during crawling (if omitted, crawling will stop only  
        when all the pages of the same domain reachable from the starting one will be crawled).
        :type max_pages_to_crawl: integer or None
        
        :param crawler_delay: To allow for polite crawling, a minimum delay between two page requests can be set (by default, 1.5 sec.s)  
        :type crawler_delay: float or DEFAULT_CRAWLER_DELAY
    '''

    self._last_crawl_time = 0
    self._queue = Queue()
    self.__queued_pages_urls = {}  #Keeps track of the pages already crawled, to avoid deadlock and endless circles
    
    try:
        max_page_depth = int(max_page_depth) 
        self._max_page_depth = max_page_depth if max_page_depth > 0 else None
    except TypeError:
        self._max_page_depth = None
    try:
        max_pages_to_crawl = int(max_pages_to_crawl)
        self.__max_pages_to_crawl = max_pages_to_crawl if max_pages_to_crawl > 0 else None
    except TypeError:
        self.__max_pages_to_crawl = None
        
    self._crawler_delay = crawler_delay
    self._page_index = 0
    self._site = {}   #Map pages' ID to the real objects
    self._url_to_page_id = {} #Map URLs to page IDs  
    self._url_depth = {} #Depth level fpr a given url
    self._queue = Queue()
    
    (self.__home_scheme, self.__home_domain, _, _ , _) = urlsplit(url)
 
    #Might be necessary if distinctions among protocols are considered
#    if home_scheme == 'https':
#      home_scheme = 'http'

    self.__home_page_url = self.format_and_enqueue_url(url, '', 0)
  
    threads = max(1, int(threads))
    
    crawler_threads = []
    for i in xrange(threads):
      crawler = Crawler(i, self)
      crawler.daemon = True #Mark the processes as deamons, so they will be terminated when program exits
      crawler_threads.append(crawler)
      crawler.start()
    
    self._queue.join()
    
    assert (self._queue.empty())
    
    #can kill any waiting thread right now, self._queue is the only shared resource and it's been released
    for crawler in crawler_threads:
      try:
        crawler.quit()
      except SystemExit:
        pass
      finally:
        assert( not crawler.is_alive() )

    return self.__home_page_url



  def list_resources(self, page_url = None):
    '''Starting from the home page (or from the page provided), lists all the resources used 
       in it and in all the pages on the same domain reachable from the home page
       
       :param page_url: It is possible to specify a page different from the one from which the crawling had started,
       and explore the connection graph from that page (it will, of course, be limited to that part of the domain actually crawled,
       if a page limit or a depth limit have been specified) 
       :type page_url: string or self.__home_page_url
    '''     
    if page_url is None:
      page_url = self.__home_page_url
    elif not page_url in self._url_to_page_id:  #Checks that the page has actually been crawled
      return {"images": Set(), "css": Set(), "scripts": Set()}  #Otherwise return an empty set
    
    pages_visited = {}
    
    def recursive_list(page, img_set, css_set, script_set):
      '''Recursively lists all the resources used by the current page and all the linked pages
      '''
      
      try:
        img_set = img_set | page._img_urls
        css_set = css_set | page._css_urls
        script_set = script_set | page._script_urls
      except: #pragma: no cover
        return img_set, css_set, script_set
      
      try:
        for link_url in page._links:
          link_page_id = self._url_to_page_id[link_url]
          if not link_page_id in pages_visited:
            pages_visited[link_page_id] = True
            img_set, css_set, script_set = recursive_list(self._site[link_page_id], img_set, css_set, script_set)
      except KeyError:
        pass
    
      return img_set, css_set, script_set
     
    pages_visited[self._url_to_page_id[page_url]] = True  
    img_set, css_set, script_set = recursive_list(self._site[self._url_to_page_id[page_url]], Set(), Set(), Set())
    return {"images": img_set, "css": css_set, "scripts": script_set}
  
  
  def page_graph(self, page_url = None):
    '''Starting from the home page (or from the page provided), draws a graph of the website.
       
       :param page_url: It is possible to specify a page different from the one from which the crawling had started,
       and explore the connection graph from that page (it will, of course, be limited to that part of the domain actually crawled, 
       if a page limit or a depth limit have been specified) 
       :type page_url: string or self.__home_page_url
    '''     
    if page_url is None:
      page_url = self.__home_page_url  #Mark the first page as visited
    elif not page_url in self._url_to_page_id:  #Checks that the page has actually been crawled
      return []  #Otherwise return an empty set
    
    pages_visited = {}
    
    def recursive_graph(page, pages_set):
      '''Recursively lists all the resources used by the current page and all the linked pages
      '''
      
      #try:
      pages_set.append({"links": page._links, "url": page._url, "depth": page._depth}) 
      #except: #pragma: no cover
      #  return pages_set
      
      try:
        for link_url in page._links:
          link_page_id = self._url_to_page_id[link_url]
          if not link_page_id in pages_visited:
            pages_visited[link_page_id] = True
            pages_set = recursive_graph(self._site[link_page_id], pages_set)
      except KeyError:
        pass
    
      return pages_set
    
    pages_visited[self._url_to_page_id[page_url]] = True  #Mark the first page as visited
    return recursive_graph(self._site[self._url_to_page_id[page_url]], [])
    