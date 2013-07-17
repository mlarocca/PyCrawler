#!/usr/bin/env python

'''
Created on 05/gen/2013

@author: mlarocca
'''
from pycrawler import CrawlerHandler
from urlparse import urlunsplit
from random import random
import logging
import os

'''UNIT + INTEGRATION TESTING'''

def test_crawler(url, threads = 1, max_page_depth = None, max_pages_to_crawl = None):
  handler = CrawlerHandler()
  handler.start_crawling(url, threads, max_page_depth, max_pages_to_crawl, 0)
  return handler.list_resources()
  #assert(len(handler.start_crawling(url)) > 0)

def test_list_resources(url, threads = 1, max_page_depth = None, max_pages_to_crawl = None):
  handler = CrawlerHandler()
  home_page = handler.start_crawling(url, threads, max_page_depth, max_pages_to_crawl, 0)
  #Looks for a page that doesn't exist
  resources = handler.list_resources(home_page + str(random()))
  for s in resources.values():
    assert(len(s) == 0) 
  #Looks for a page that DOES exist
  resources = handler.list_resources(home_page)
  assert(len( reduce(lambda s1, s2: s1 | s2, resources.values())) > 0) #At least some resource should be found
   
def test_page_graph(url, threads = 1, max_page_depth = None, max_pages_to_crawl = None):
  handler = CrawlerHandler()
  home_page = handler.start_crawling(url, threads, max_page_depth, max_pages_to_crawl, 0)
  #Looks for a page that doesn't exist
  pages_set = handler.page_graph(home_page + str(random()))
  assert(len(pages_set) == 0) 
  #looks for a page that DOES exist
  pages_set_1 = handler.page_graph(home_page)
  pages_set_2 = handler.page_graph()
  assert (pages_set_1 == pages_set_2)
  return pages_set_2
  #At least some resource should be found   
   
def test():

  print test_crawler("http://repubblica.it", 30, None, 20)
  
  path = "/%s/tests" % os.getcwd().replace("\\", "/")
                   
  #Test cyclic reference between 2 documents 
  site_resources = test_crawler(urlunsplit(("file", path, "test_1.html", '', '')), 3)
  
  #Asserts on content
  assert("img_2.jpg" in site_resources["images"])
  assert("http://mysite.me/img_1.jpg" in site_resources["images"])
  assert("/test.js" in site_resources["scripts"])

  
  #Test cyclic reference between 3 or more documents 
  site_resources = test_crawler(urlunsplit(("file", path, "test_B.html", '', '')), 2)

  #Asserts on content
  assert("img_2.jpg" in site_resources["images"])
  assert("http://mysite.me/img_1.jpg" in site_resources["images"])
  assert("/test.js" in site_resources["scripts"])
  assert("img_3.jpg" in site_resources["images"])  
  url_B = urlunsplit(("file", path, "test_B.html", '', ''))
  test_list_resources(url_B, 2)
  
  print test_page_graph(url_B, 2, 1)
  print test_page_graph(url_B, 2)
  
  graph = test_page_graph(urlunsplit(("file", path, "test_B.html", '', '')), 5)
  url1 = urlunsplit(("file", path, "test_1.html", '', ''))
  url2 = urlunsplit(("file", path, "test_1_copy.html", '', ''))
  
  assert(graph[url1] == graph[url2])  
  assert len(graph[url_B]["resources"]["videos"]) == 2
  print graph[url_B]["resources"]["audios"]
  #assert graph[url_B]["resources"]["audios"] == set(['audio_test3.ogg', 'audio_test3.mp4'])
'''END OF TESTING'''



'''PROFILING'''
def __profile_run(): #pragma: no cover
  test_crawler("http://techland.time.com/2012/09/19/nasa-actually-working-on-faster-than-light-warp-drive/", 5, None, 100)
  
def profile(): #pragma: no cover
  import cProfile

  cProfile.run('__profile_run()', 'crawler_profile.txt')
  
  import pstats
  p = pstats.Stats('crawler_profile.txt')
  p.sort_stats('time').print_stats(20)
    
'''END OF PROFILING'''
  
  
  
#if __name__ == '__main__':
  #Keep a log to give signals of its activity
logging.basicConfig(filename='crawler.log', level = logging.DEBUG)  #logging.DEBUG
  
test()
#  profile() 