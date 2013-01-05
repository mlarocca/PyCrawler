'''
Created on 05/gen/2013

@author: mlarocca
'''
from crawler import CrawlerHandler, strip_comments, extract_A_href, extract_form_action, extract_link_href, extract_img_src, extract_script_src
import logging
import thread
import os

def test_crawler(url, threads = 1, max_pages_to_crawl = None):
  handler = CrawlerHandler()
  home_page = handler.start_crawling(url, threads, max_pages_to_crawl, 0)
  return handler.list_resources(home_page)
  #assert(len(handler.start_crawling(url)) > 0)

'''UNIT TESTING'''

'''Tests regular expressions to extract urls from HTML
'''
def test_reg_exp(): 
  assert(strip_comments("<a><!-- fsdhgfjkhf -->Casa--></a>") == "<a>Casa--></a>") 
  test_str = """<a href='pollo'> Casa </A>  gibberish
                            <script src='/test.js'> sss</script>
                          <A   style='sdffhldshfsk'      href="chicken"> Home </a> </ 
                          <img<form method='get' action='gggggggrande'
                          <img  src='spider.jpg'
                          <a     src='prova'>
                          """
  tmp = extract_A_href(test_str)  
  assert("pollo" in tmp and 'chicken'in tmp and len(tmp) == 2)
  tmp = extract_link_href(test_str)  
  assert(len(tmp) == 0)
  tmp = extract_script_src(test_str)  
  assert("/test.js" in tmp and len(tmp) == 1)
  tmp = extract_img_src(test_str)
  assert("spider.jpg" in tmp and len(tmp) == 1)
  tmp = extract_form_action(test_str)
  assert("gggggggrande" in tmp and len(tmp) == 1)

  test_str = """ <link rel="shortcut icon" href="http://cdn.sstatic.net/stackoverflow/img/favicon.ico">
    <link rel="apple-touch-icon" href="http://cdn.sstatic.net/stackoverflow/img/apple-touch-icon.png">
    <link rel="search" type="application/opensearchdescription+xml" title="Stack Overflow" href="/opensearch.xml">
                          """  
  tmp = extract_A_href(test_str)  
  assert(len(tmp) == 0)  
  tmp = extract_link_href(test_str)  
  assert("http://cdn.sstatic.net/stackoverflow/img/favicon.ico" in tmp and len(tmp) == 3)
  
  test_str = """   <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
    <script type="text/javascript" src="http://cdn.sstatic.net/js/stub.js?v=8a629d6e9fb6"></script><form method='post' action='gggggggrande'
    <link rel="stylesheet" type="text/css" href="http://cdn.sstatic.net/stackoverflow/all.css?v=24fdd40e5473">"""
  tmp = extract_script_src(test_str)  
  assert("http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js" in tmp and len(tmp) == 2)
  tmp = extract_img_src(test_str)
  assert(len(tmp) == 0)    
  tmp = extract_A_href(test_str)  
  assert(len(tmp) == 0)  
  tmp = extract_form_action(test_str)  
  assert(len(tmp) == 0)  

    
def test():

  test_crawler("http://repubblica.it", 30, 20)
    
  test_reg_exp()  
  
  path = "file:///%s/" % os.getcwd().replace("\\", "/")
  
  #Test cyclic reference between 2 documents 
  site_resources = test_crawler(path + "tests/test_1.html", 3)
  
  #Asserts on content
  assert("img_2.jpg" in site_resources["images"])
  assert("http://mysite.me/img_1.jpg" in site_resources["images"])
  assert("/test.js" in site_resources["scripts"])
  
  #Test cyclic reference between 3 or more documents 
  site_resources = test_crawler(path + "tests/test_B.html", 2)

  #Asserts on content
  assert("img_2.jpg" in site_resources["images"])
  assert("http://mysite.me/img_1.jpg" in site_resources["images"])
  assert("/test.js" in site_resources["scripts"])
  assert("img_3.jpg" in site_resources["images"])  
  

   
'''END OF UNIT TESTING'''

'''PROFILING'''
def __profile_run(): #pragma: no cover
  test_crawler("http://techland.time.com/2012/09/19/nasa-actually-working-on-faster-than-light-warp-drive/", 100)
  
def profile(): #pragma: no cover
  import cProfile

  cProfile.run('__profile_run()', 'crawler_profile.txt')
  
  import pstats
  p = pstats.Stats('crawler_profile.txt')
  p.sort_stats('time').print_stats(20)
    
'''END OF PROFILING'''
if __name__ == '__main__':
  #Keep a log to give signals of its activity
  logging.basicConfig(filename='crawler.log', level = logging.INFO)  #logging.DEBUG
  

  test()
#  profile() 