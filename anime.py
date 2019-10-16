import urllib.request as Web
from bs4 import BeautifulSoup as bs4

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from qbittorrent import Client

qb = Client('http://127.0.0.1:8080/')
# 'Bypass from localhost' should be enabled

# TODO: Check if this drive is full, and switch to an available one
DL_PATH = "E:/Torrents/"
headers = {}
headers['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"
req = Web.Request('https://horriblesubs.info/current-season/', headers=headers)
src = Web.urlopen(req).read()
parser = bs4(src, features='html.parser')
divs = parser.body.find_all('div', attrs={'class': 'ind-show'})
size = len(divs)

for i, div in enumerate(divs):
    driver = webdriver.Firefox()
    driver.get('https://horriblesubs.info' + div.a['href'])
    WebDriverWait(driver, 50).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'rls-info-container')))

    # Expand the whole listing to get all the episodes
    elem = driver.find_element_by_class_name('show-more')
    while elem.text != 'No more results':
        elem.click()
        elem = driver.find_element_by_class_name('show-more')

    src = driver.page_source
    driver.close()
    parser = bs4(src, features='html.parser')
    hs = parser.body\
        .find('div', attrs={'class': 'hs-shows'})\
        .find_all('div', attrs={'class': 'rls-info-container'})
    
    for block in hs:
        # TODO: If a resolution is updated, delete the lower resolution alternative on disk
        link_rel = block.find('div', attrs={'class': 'rls-link link-1080p'})

        if (link_rel is None):
            link_rel = block.find('div', attrs={'class': 'rls-link link-720p'})

        if (link_rel is None):
            link_rel = block.find('div', attrs={'class': 'rls-link link-480p'})

        if (link_rel is not None):
            magnet = link_rel.find('a', attrs={'title': 'Magnet Link'})['href']
            qb.download_from_link(magnet, category='anime', savepath=DL_PATH + div.a.text)
    
    print('Progress: ' + str(round(((i + 1) / size) * 100, 2)) + '%')