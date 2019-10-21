import os
import traceback

from sys import platform
from shutil import rmtree

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

import urllib.request as Web
from bs4 import BeautifulSoup as Soup
from qbittorrent import Client as qBittorrent
from wget import download
from collections import defaultdict


def get_dl_path():
    # TODO: Check if this drive has space, else check another drive
    # if there's no free space, crash
    return 'E:/Torrents/'


def get_addons_path():
    path = os.getcwd()

    if platform == 'win32':
        path += '\\addons\\'
    else:
        path += '/addons/'

    if not os.path.exists(path):
        os.mkdir(path)

    return path


dl_path = get_dl_path()
addons_path = get_addons_path()
profile = webdriver.FirefoxProfile()

# Run the browser in private mode
profile.set_preference('extensions.allowPrivateBrowsingByDefault', True)
profile.set_preference('browser.privatebrowsing.autostart', True)

# Privacy settings (https://www.privacytools.io/)
profile.set_preference('media.peerconnection.turn.disable', True)
profile.set_preference('media.peerconnection.use_document_iceservers', False)
profile.set_preference('media.peerconnection.video.enabled', False)
profile.set_preference('media.peerconnection.identity.timeout', 1)
profile.set_preference('privacy.firstparty.isolate', True)
profile.set_preference('privacy.resistFingerprinting', True)
profile.set_preference('privacy.trackingprotection.fingerprinting.enabled', True)
profile.set_preference('privacy.trackingprotection.cryptomining.enabled', True)
profile.set_preference('privacy.trackingprotection.enabled', True)
profile.set_preference('browser.send_pings', False)
profile.set_preference('browser.sessionstore.max_tabs_undo', 0)
profile.set_preference('browser.sessionstore.privacy_level', 2)
profile.set_preference('browser.urlbar.speculativeConnect.enabled', False)
profile.set_preference('dom.event.clipboardevents.enabled', False)
profile.set_preference('media.eme.enabled', False)
profile.set_preference('media.gmp-widevinecdm.enabled', False)
profile.set_preference('media.navigator.enabled', False)
profile.set_preference('network.cookie.cookieBehavior', 2)
profile.set_preference('network.cookie.lifetimePolicy', 2)
profile.set_preference('network.http.referer.XOriginPolicy', 2)
profile.set_preference('network.http.referer.XOriginTrimmingPolicy', 2)
profile.set_preference('network.IDN_show_punycode', True)
profile.set_preference('webgl.disabled', True)

# Settings unique to https://restoreprivacy.com/firefox-privacy/
profile.set_preference('geo.enabled', False)
profile.set_preference('media.peerconnection.enabled', False)
profile.set_preference('network.dns.disablePrefetch', True)
profile.set_preference('network.prefetch-next', False)

options = webdriver.FirefoxOptions()
options.headless = True

browser = webdriver.Firefox(firefox_profile=profile, options=options)

ext_prefix = 'https://addons.mozilla.org/en-US/firefox/addon/'
exts = [
    # 'ublock-origin',  # Blocks ads & such
    # 'https-everywhere',  # TODO: Figure out how to enable 'Encryt All Sites Eligble'
    # 'decentraleyes',  # Blocks Content Management Systems and handles their abilities locally
    'umatrix'  # Will block Disqus on HorribleSubs automatically
]

for ext in exts:
    browser.get(ext_prefix + ext)
    btn = browser.find_element_by_class_name('AMInstallButton')
    ref = btn.find_element_by_tag_name('a').get_attribute('href')
    url = ref.split('?')[0]
    addon = download(url, out=addons_path).replace('/', '')
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

        # Wait to dodge `selenium.common.exceptions.ElementNotInteractableException: Message: Element could not be scrolled into view`
        WebDriverWait(browser, 15).until(EC.element_to_be_clickable((By.CLASS_NAME, 'more-button')))

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
                season[dl_path + div.a.text].append(magnet)

        print('Progress:', round(((i + 1) / size) * 100, 2), '%')
except Exception:
    print(traceback.print_exc())
finally:
    browser.quit()
    rmtree(addons_path)

try:
    # Web UI -> 'Bypass authentication for hosts on localhost' should be enabled
    # Downloads -> 'Do not start download automatically' should be enabled
    qb = qBittorrent('http://127.0.0.1:8080/')

    # Use DP to decrease show fetch time
    for path, magnets in season.items():
        for magnet in magnets:
            qb.download_from_link(magnet, savepath=path, category='anime')

    qb.resume_all()
except ConnectionError:
    print('[!] qBittorrent not active!')
