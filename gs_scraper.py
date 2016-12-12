# -*- coding: utf-8 -*-
##############################################################
# SCRAPE GOOGLE SCHOLAR RESULTS TO CSV
# Author: Nathaniel Henry
# Inspired by https://github.com/ckreibich/scholar.py
# 
#  This program takes as input a URL from the first page of 
#    your Google Scholar results. It then iterates through
#    pages (until there is no link to a next page) and scrapes
#    information about all results. These are stores in a Pandas
#    DataFrame and then writted to a csv.
#
# Dependencies: numpy, pandas, requests, browser_cookie3, BeautifulSoup
# Tested in Python 3 (but should be usable in 2.7 with minor changes)
# Note 1: I'm planning to make this code more modular soon
# Note 2: The "sleep" function at the end of the while loop needs 
#   to be refined (+ time?) to avoid Google Scholar blocking us
##############################################################


##############################################################
# I. ENTER INFORMATION HERE
##############################################################

# REQUIRED: COPY AND PASTE THE FOLDER WHERE YOU WILL STORE THE OUTPUT DATA
# MAKE SURE THE r REMAINS IN FRONT OF THE STRING, eg. r'C:\path\to\my_directory\"
workdir = r"C:\Users\nathenry\Documents\TEST"

# REQUIRED: ENTER THE NAME OF THE FILE YOU WANT TO WRITE TO, WITH A CSV EXTENSION
outfile = "google_scholar_exports_test.csv"

# REQUIRED: ENTER THE URL OF YOUR FIRST PAGE OF GOOGLE SCHOLAR HERE
start_url = "https://scholar.google.com/scholar?hl=en&q=%22geogames%22+%22virtual+reality%22&btnG=&as_sdt=1%2C48&as_sdtp="

# IMPORTANT: Enter the maximum number of records you want to extract
# If you know how many results this search returns, enter that number or higher
# This ensures that the program doesn't loop infinitely
max_records = 5000

# The URL request function also passes in headers
# Advanced users can change these:
hdr = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.2; de; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5'}

##############################################################
# CODE BEGINS HERE
# II. Import modules, define functions
##############################################################
import re
import sys
from os.path import join
import numpy as np
import pandas as pd
import requests
from time import sleep
import browser_cookie3


# Import URL libraries - try for Python 3 first, fall back to 2
try:
    # pylint: disable-msg=F0401
    # pylint: disable-msg=E0611
    from urllib.request import HTTPCookieProcessor, Request, build_opener
    from urllib.parse import quote, unquote
    from http.cookiejar import MozillaCookieJar
except ImportError:
    # Fallback for Python 2
    from urllib2 import Request, build_opener, HTTPCookieProcessor
    from urllib import quote, unquote
    from cookielib import MozillaCookieJar

# Import BeautifulSoup -- try 4 first, fall back to older
try:
    from bs4 import BeautifulSoup
except ImportError:
    try:
        from BeautifulSoup import BeautifulSoup
    except ImportError:
        print('We need BeautifulSoup, sorry...')
        sys.exit(1)

# Support unicode in both Python 2 and 3. In Python 3, unicode is str.
if sys.version_info[0] == 3:
    unicode = str # pylint: disable-msg=W0622
    encode = lambda s: unicode(s) # pylint: disable-msg=C0103
else:
    def encode(s):
        if isinstance(s, str):
            return s.encode('utf-8') # pylint: disable-msg=C0103
        else:
            return str(s)

# This function takes a BeautifulSoup object and returns a string using get_text
# If the BeautifulSoup object returns "None", the function returns an empty string
def safe_str_bs4(in_soup=""):
    try:
        if in_soup.get_text() is not None:
            return str(in_soup.get_text()).lstrip()
        else:
            return ''
    except AttributeError:
        return ''
            
##############################################################
# III. Iterate through pages, extracting results and next page link
##############################################################

# Populate some key variables:
# The URL that will be read in this iteration
current_url = start_url
# Cookies for the URL request
cj = browser_cookie3.chrome()
# The current page number
page_num = 0
# This variable determines when the page-reading loop will end
end_of_pages = False
# The number of records extracted
records_extracted = 0
# A list of all the records, in Pandas Dataframe format
all_dfs_list = []



while end_of_pages == False:
    # Increment page
    page_num += 1
    page_html = ''
    
    # Open the page and extract text, or else end the loop
    try:
        # Requests the URL and opens the page
        myreq = requests.get(current_url,headers=hdr,cookies=cj)
        # Extracts the HTML as a string
        print("Opened page #%s: %s" % (str(page_num),current_url))
        page_html = myreq.text
    except:
        # This means that the URL request didn't work
        print("Error occurred trying to read page #%s: %s" % ((str(page_num), current_url)))
        end_of_pages = True
        break
    
    # Parse the page HTML into BeautifulSoup
    page_soup = BeautifulSoup(page_html, "html.parser")    
    # Results on the page are stored within separate "gs_r" divs
    page_results = page_soup.find_all("div",class_="gs_r")
    if len(page_results) == 0:
        print("##############################################")
        print("No results in page. Breaking loop.")
        print("Note: This may mean that you have been temporarily blocked from Google Scholar.")
        print("Try logging onto Google Scholar in Chrome, Firefox, or IE and completing the user authentication.")
        print("##############################################")
        break
    
    ##############################################################
    # V. Iterate through results, extracting info
    ##############################################################
    
    for result_soup in page_results:
        # This is the HTML for a single result
        # Separate the result HTML into titles, author + journal info, and descriptions
        title_html = result_soup.find("h3",class_="gs_rt")
        authors_journal_year_html = result_soup.find("div",class_="gs_a")
        desc_html = result_soup.find("div",class_="gs_rs")
        # Extract links on the side
        all_links = result_soup.find_all("div",class_="gs_ggsd")
        
        # If the title also contains a link, append the link HTML to all_links
        if title_html.find("a") is not None:
            all_links = all_links + [title_html]
    
        # Extract text from the HTML data    
        # TITLE
        result_title = safe_str_bs4(title_html)
        # Remove any text in square brackets at the beginning of the title
        while re.search("^\[[a-z|A-Z]{1,12}\]",result_title) is not None:
            rm_index = result_title.index(']') + 1
            result_title = result_title[rm_index:]
        # Strip any remaining whitespace from the title
        result_title = result_title.lstrip()
        
        # AUTHORS, JOURNAL, YEAR
        authors_journal_year_text = safe_str_bs4(authors_journal_year_html)
        
        # Initialize the variables which will be filled
        result_authors = ''
        result_journal_year = ''
        result_journal_site = ''
        result_journal = ''
        result_author = ''
        if authors_journal_year_text != '':
            # General format for this line of text:
            # Authors - Journal, year - journal website
            # Any of these fields can be missing from this line
            # First, split the text on dashes
            fields_list = authors_journal_year_text.split(' - ')
            # Try to identify each field in the list, using increasingly broad logic to assign
            # Only test fields that haven't already been assigned
            for field in fields_list:
                if ((re.search("[1-2][0-9]{3}",field[-4:])) is not None) and (result_journal_year == ''):
                    # A date in the field suggest that this is the journal/year field
                    result_journal_year = field
                elif (re.search("(\.[a-z]{2,3})|(([a-z]+\.){2}[a-z])|(^http)",field)) and (result_journal_site == ''):
                    # This suggests that the field contains a URL
                    result_journal_site = field
                elif (re.search('([A-Z][ ]?){1,2} [A-Z]',field)) and (result_authors == ''):
                    # This suggests that the field contains a name
                    result_authors = field
                elif (field.count(',') > 0) and (result_authors == ''):
                    # This suggests that the field contains a list of author names
                    # This will not consider (journal), (year) combos, which have already been considered
                    results_authors = field
                elif (field.count(',') > 0) and (result_journal_year == ''):
                    # Less commonly, the journal title may have commas in it
                    result_journal_year = field
                elif result_journal_year == '':
                    # If none of the other fields work, perhaps it's a journal title
                    result_journal_year = field
                elif result_authors == "":
                    # Otherwise, add it to the author field
                    result_authors = field
                elif result_journal_year == "":
                    # Otherwise, add it to the journal_site field
                    result_journal_year = field
                # You can add more elif statements to the switching logic above
            # Now, populate the result_journal and result_year fields
            if result_journal_year != '':
                if (re.search("[1-2][0-9]{3}",result_journal_year[-4:]) is not None) and (result_journal_year.count(', ') > 0):
                    # There is probably a year
                    result_year = result_journal_year[-4:]
                    result_journal = result_journal_year[:-6]
                else:
                    # There probably isn't a year
                    result_journal = result_journal_year
                    
        # DESCRIPTION
        result_desc = safe_str_bs4(desc_html)
        # Replace newline characters with spaces in the description
        result_desc = re.sub('\n',' ',result_desc)
    
        
        # Iterate through links found in the result
        result_links = []
        for one_link in all_links:
            link_text = one_link.get_text()
            link_url = one_link.a.get('href')
            # If the link begins with a forward slash, then it's an internal link from Google Scholar
            if re.match(r"^/",link_url) is not None:
                link_url = "https://scholar.google.com" + link_url
            result_links.append(link_url)
        if len(result_links) < 4:
            # Will fill all missing values with empty strings up to result_links[3]
            result_links = result_links + (['']*(4-len(result_links)))
    
        # Create a dict storing all of the results for this page  
        # If you want to change these, remember to change the list at the bottom as well
        together_dict = {'title': result_title,
                         'authors': result_authors,
                         'journal': result_journal,
                         'journal_website': result_journal_site,
                         'year': result_year,
                         'description': result_desc,
                         'link_1': result_links[0],
                         'link_2': result_links[1],
                         'link_3': result_links[2],
                         'link_4': result_links[3]}
        # Use the dict to create a new pandas dataframe        
        new_df = pd.DataFrame([together_dict])
        # Append the dataframe to a list of dataframes
        all_dfs_list.append(new_df)
        # Finally, increment the number of results captured by 1
        records_extracted += 1

    # Outside of the results loop, back to searching through the page
    # Find the link to the next page, if it exists
    nav_next_span = page_soup.find("span",class_="gs_ico_nav_next")
    if (nav_next_span is not None) and (nav_next_span.parent.get('href') is not None):
        # In this case, there is a link to the next page
        current_url = "https://scholar.google.com" + nav_next_span.parent.get('href')
    else:
        # In this case, there is no link to the next page
        end_of_pages = True
    # Sleep for 2-3 seconds to make sure that Google Scholar doesn't block this program
    sleep(2 + np.random.random())
    # Safeguard using the max_records variable defined above
    if (end_of_pages == False) and (records_extracted >= max_records):
        print("We have reached the maximum number of records (%s). Exiting the page." % str(max_records))
        end_of_pages = True


# Outside of the page loop    
# Once all of the pages have been extracted:
# Concatenate all of the dataframes into one
empty_dict = {'title': '',
              'authors': '',
              'journal': '',
              'journal_website': '',
              'year': '',
              'description': '',
              'link_1': '',
              'link_2': '',
              'link_3': '',
              'link_4': ''}

full_df = pd.DataFrame([empty_dict])
if len(all_dfs_list) > 0:
    full_df = pd.concat(all_dfs_list)

# Sort the df by column:
col_list = ['authors','title','description','year','journal','journal_website','link_1','link_2','link_3','link_4']
full_df = full_df.ix[:,col_list]
full_df.to_csv(join(workdir,outfile),index=False)

print("Finished! Scraped %s pages and extracted %s records in total." % (str(page_num),str(records_extracted)))
