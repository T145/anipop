import os
from typing import Dict, Any
from shutil import rmtree
from wget import download
from collections import defaultdict

import urllib.request as Web
from bs4 import BeautifulSoup as Soup

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from qbittorrent import Client as qBittorrent


profile = webdriver.FirefoxProfile()

profile_settings: Dict[str, Any] = {
    'extensions.allowPrivateBrowsingByDefault': True,
    'browser.privatebrowsing.autostart': True,
    'media.peerconnection.turn.disable': True,
    'media.peerconnection.use_document_iceservers': False,
    'media.peerconnection.video.enabled': False,
    'media.peerconnection.identity.timeout': 1,
    'privacy.firstparty.isolate': True,
    'privacy.resistFingerprinting': True,
    'privacy.trackingprotection.fingerprinting.enabled': True,
    'privacy.trackingprotection.cryptomining.enabled': True,
    'privacy.trackingprotection.enabled': True,
    'browser.send_pings': False,
    'browser.sessionstore.max_tabs_undo': 0,
    'browser.sessionstore.privacy_level': 2,
    'browser.urlbar.speculativeConnect.enabled': False,
    'dom.event.clipboardevents.enabled': False,
    'media.eme.enabled': False,
    'media.gmp-widevinecdm.enabled': False,
    'media.navigator.enabled': False,
    'network.cookie.cookieBehavior': 2,
    'network.cookie.lifetimePolicy': 2,
    'network.http.referer.XOriginPolicy': 2,
    'network.http.referer.XOriginTrimmingPolicy': 2,
    'network.IDN_show_punycode': True,
    'webgl.disabled': True,
    'geo.enabled': False,
    'media.peerconnection.enabled': False,
    'network.dns.disablePrefetch': True,
    'network.prefetch-next': False
}

for setting_name, setting_value in profile_settings.items():
    profile.set_preference(setting_name, setting_value)

options = webdriver.FirefoxOptions()
options.headless = True

browser = webdriver.Firefox(firefox_profile=profile, options=options)

ext_prefix = 'https://addons.mozilla.org/en-US/firefox/addon/'
exts = [
    'ublock-origin',  # Blocks ads & such
    # 'https-everywhere',  # TODO: Figure out how to enable 'Encryt All Sites Eligble'
    # 'decentraleyes',  # Blocks Content Management Systems and handles their abilities locally
    'umatrix'  # Will block Disqus on HorribleSubs automatically
]

addons_path = os.path.normpath(os.path.join(os.getcwd(), 'addons'))

if not os.path.exists(addons_path):
    os.mkdir(addons_path)

for ext in exts:
    browser.get(ext_prefix + ext)
    btn = browser.find_element_by_class_name('AMInstallButton')
    ref = btn.find_element_by_tag_name('a').get_attribute('href')
    url = ref.split('?')[0]
    addon = os.path.normpath(download(url, out=addons_path))
    browser.install_addon(addon, temporary=True)

browser.get('https://horriblesubs.info/current-season/')
src = browser.page_source
parser = Soup(src, features='html.parser')
divs = parser.body.find_all('div', attrs={'class': 'ind-show'})
size = len(divs)
season = defaultdict(list)

print('\nDownloading', size, 'shows')

try:
    for i, div in enumerate(divs):
        browser.get('https://horriblesubs.info' + div.a['href'])

        # Wait to dodge `selenium.common.exceptions.ElementNotInteractableException`
        WebDriverWait(browser, 15)\
            .until(EC.element_to_be_clickable((By.CLASS_NAME, 'more-button')))

        # Expand the whole listing to get all the episodes
        if not browser.find_elements_by_id('01'):
            try:
                while True:
                    browser.find_element_by_class_name('more-button').click()
            except NoSuchElementException:
                pass

        src = browser.page_source
        parser = Soup(src, features='html.parser')
        episodes = parser.body\
            .find('div', attrs={'class': 'hs-shows'})\
            .find_all('div', attrs={'class': 'rls-info-container'})

        for episode in episodes:
            links = [
                episode.find('div', attrs={'class': 'rls-link link-480p'}),
                episode.find('div', attrs={'class': 'rls-link link-720p'}),
                episode.find('div', attrs={'class': 'rls-link link-1080p'})
            ]
            magnet = None

            for link in links:
                if link is not None:
                    a = link.find('a', attrs={'title': 'Magnet Link'})
                    if a is not None:
                        magnet = a['href']

            if magnet is not None:
                season[div.a.text].append(magnet)

        print('[%]', round(((i + 1) / size) * 100, 3))
finally:
    browser.quit()
    rmtree(addons_path)


def get_dl_path():
    # TODO: Check if this drive has space, else check another drive
    # if there's no free space, crash
    return 'E:/Torrents/'


try:
    # Web UI -> 'Bypass authentication for hosts on localhost' should be enabled
    # Downloads -> 'Do not start download automatically' should be enabled
    qb = qBittorrent('http://127.0.0.1:8080/')

    # Use DP to decrease show fetch time
    for path, magnets in season.items():
        for magnet in magnets:
            qb.download_from_link(magnet, savepath=get_dl_path() + path, category='anime')

    qb.resume_all()
except ConnectionError:
    print('[!] qBittorrent not active!')
