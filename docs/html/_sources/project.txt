Project Summary
===============
  
Info
----

Created on 28/nov/2012
Revised on 05/jan/2013

Author: Marcello La Rocca
 
Description 
-----------

PyCrawler is a Breadth-first multithread crawler, keeping a queue of 
the URLs that are encountered.
Main class is CrawlHandler. Once created, crawling can be started on 
any page using start_crawling(url). It is possible to crawl only one site 
at the same time.

It is possible to hand over three extra parameters to start_crawling:
    * The number of threads to be started (each thread will pick up links from a shared synchronized queue and process them);
    * A limit to the number of pages crawled;
    * A delay between two consecutive requests of a single Crawler (to allow for polite crawling, default is 0.15 seconds)

The actual crawling is made by class Crawler: each instance of Crawler runs
in a separate thread.
A list of pages already visited is used to avoid circular
redirection between pages.
   
Assumptions
-----------  

Only crawls static content
 * Anchors
 * Imgs
 * Scripts
 * Stylesheets
 * Forms (only those using get method)
Discards query parameters and #fragments
URLs can't contain quotes or double quotes
Relocation and forms submission by javascript are ignored
Doesn't check if tags are well formes, and well placed (f.i. if A and FORM only appears in body section)
Only URLs on the same domain are listed  