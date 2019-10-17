import os
import shutil

from qbittorrent import Client
import urllib.request as Web
from bs4 import BeautifulSoup as Soup
import wget

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# TODO: Check if this drive is full, and switch to an available one
DL_PATH = 'E:/Torrents/'
ADDONS_PATH = os.getcwd() + '\\addons\\'
QB = Client('http://127.0.0.1:8080/')
# 'Bypass from localhost' should be enabled


def get_browser():
    os.mkdir(ADDONS_PATH)
    ext_prefix = 'https://addons.mozilla.org/en-US/firefox/addon/'
    exts = [
        'ublock-origin',  # Blocks ads & such
        'umatrix',  # Will block Disqus on HorribleSubs automatically
        'https-everywhere',  # TODO: Figure out how to enable 'Encryt All Sites Eligble'
        'decentraleyes',  # Blocks Content Management Systems and handles their abilities locally
    ]
    profile = webdriver.FirefoxProfile()

    # Download settings (in case a more efficient means of downloading XPIs through the browser is discovered)
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.download.dir', ADDONS_PATH)
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/x-gzip')

    # Privacy settings (https://restoreprivacy.com/firefox-privacy/)
    # TODO: Cross-reference w/ https://www.privacytools.io/
    # profile.set_preference('browser.privatebrowsing.autostart', True) # TODO: Figure out how to allow addons in PB
    profile.set_preference('media.peerconnection.enabled', False)
    profile.set_preference('privacy.resistFingerprinting', True)
    profile.set_preference('privacy.trackingprotection.fingerprinting.enabled', True)
    profile.set_preference('privacy.trackingprotection.cryptomining.enabled', True)
    profile.set_preference('privacy.firstparty.isolate', True)
    profile.set_preference('privacy.trackingprotection.enabled', True)
    profile.set_preference('geo.enabled', False)
    profile.set_preference('media.navigator.enabled', False)
    profile.set_preference('network.cookie.cookieBehavior', 2)
    profile.set_preference('network.cookie.lifetimePolicy', 2)
    profile.set_preference('network.dns.disablePrefetch', True)
    profile.set_preference('network.prefetch-next', False)
    profile.set_preference('webgl.disabled', True)
    profile.set_preference('dom.event.clipboardevents.enabled', False)
    profile.set_preference('media.eme.enabled', False)

    browser = webdriver.Firefox(firefox_profile=profile)

    for ext in exts:
        browser.get(ext_prefix + ext)
        btn = browser.find_element_by_class_name('AMInstallButton')
        ref = btn.find_element_by_tag_name('a').get_attribute('href')
        url = ref.split('?')[0]
        wget.download(url, out=ADDONS_PATH)

    for cwd, _, addons in os.walk(ADDONS_PATH):
        for addon in addons:
            addon_path = os.path.join(cwd, addon)
            browser.install_addon(addon_path, temporary=True)

    # Just to escape out of wget's printed progress bar to normalize future logging
    print('\n')

    return browser


def quit(browser):
    browser.quit()
    shutil.rmtree(ADDONS_PATH)


if __name__ == "__main__":
    browser = get_browser()
    browser.get('https://horriblesubs.info/current-season/')
    src = browser.page_source
    parser = Soup(src, features='html.parser')
    divs = parser.body.find_all('div', attrs={'class': 'ind-show'})
    size = len(divs)
    print('Downloading ', size, ' shows')

    # BUG: Doesn't iterate over all the shows
    for i, div in enumerate(divs):
        browser.get('https://horriblesubs.info' + div.a['href'])

        # Wait to dodge `selenium.common.exceptions.ElementNotInteractableException: Message: Element <div class="show-more"> could not be scrolled into view`
        WebDriverWait(browser, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'show-more')))

        # Expand the whole listing to get all the episodes
        elem = browser.find_element_by_class_name('show-more')
        while elem.text != 'No more results':
            elem.click()

        src = browser.page_source
        parser = Soup(src, features='html.parser')
        hs = parser.body\
            .find('div', attrs={'class': 'hs-shows'})\
            .find_all('div', attrs={'class': 'rls-info-container'})

        for block in hs:
            link_rel = block.find('div', attrs={'class': 'rls-link link-1080p'})

            if (link_rel is None):
                link_rel = block.find('div', attrs={'class': 'rls-link link-720p'})

            if (link_rel is None):
                link_rel = block.find('div', attrs={'class': 'rls-link link-480p'})

            if (link_rel is not None):
                magnet = link_rel.find('a', attrs={'title': 'Magnet Link'})['href']
                QB.download_from_link(magnet, category='anime', savepath=DL_PATH + div.a.text)

        print('Progress: ', round(((i + 1) / size) * 100, 2), '%')

    quit(browser)
