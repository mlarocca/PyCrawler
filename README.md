# Breadth-First, Parallel Static Crawler written in Python
==========================================================


## News 2013/07/17
   
**Version 1.3.2** released

* HTML5 video and audio tags are now supported

* Relative URLs in the dictionary returned by *pages_graph* are now translated into absolute ones


## News 2013/07/16
   
**Version 1.3** released

* Avoid duplicate pages to be parsed again

* *PageParser* constructor has been changed (now requires a second parameter, a reference to the crawler handler)

* *check_page_by_content* method added to CrawlerHandler: checks if a page has been visited by examining its content

* *pages_graph* now returns a dictionary with page's urls as keys



## News 2013/01/13
   
**Version 1.2** released

* Introduces the concept of depth in the crawling process, allowing to specify a predefined maximum depth for the
web pages to crawl, in alternative or together with a limit for the number of pages retrieved.
Consequently, the interface of *start_crawling* method has slightly changed (See documentation)

* *pages_graph* method added to CrawlerHandler: it creates a summarizing graph-like object starting from any page

## Documentation
 
http://mlarocca.github.io/PyCrawler/

## Coverage Testing results
    
https://github.com/mlarocca/PyCrawler/tree/master/coverage_testing
   