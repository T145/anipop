from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Any
import os
import wget
import sys
from bs4 import BeautifulSoup
from collections import defaultdict
from qbittorrent import Client


def get_browser():
    profile = webdriver.FirefoxProfile()
    settings: Dict[str, Any] = {
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

    for k, v in settings.items():
        profile.set_preference(k, v)

    opts = webdriver.FirefoxOptions()
    opts.headless = True
    browser = webdriver.Firefox(
        firefox_profile=profile, options=opts, service_log_path=None)
    ext_prefix = 'https://addons.mozilla.org/en-US/firefox/addon/'
    addons_path = os.path.normpath(os.path.join(os.getcwd(), 'addons'))

    if not os.path.exists(addons_path):
        os.mkdir(addons_path)

    for ext in [
        'ublock-origin',
        'https-everywhere',
        'decentraleyes',
        'clearurls',
        'umatrix'
    ]:
        browser.get(ext_prefix + ext)

        btn = browser.find_element_by_class_name('AMInstallButton')
        ref = btn.find_element_by_tag_name('a').get_attribute('href')
        url = ref.split('?')[0]
        addon = os.path.join(addons_path, wget.filename_from_url(url))

        if not os.path.isfile(addon):
            wget.download(url, out=addons_path)

        browser.install_addon(addon, temporary=True)

    return browser


def get_magnet(link):
    if link:
        a = link.find('a', attrs={'title': 'Magnet Link'})

        if a:
            return a['href']

    return None


def get_dl_path():
    # TODO: Check if this drive has space, else check another drive
    # if there's no free space, crash
    return 'M:/'


if __name__ == "__main__":
    browser = get_browser()
    browser.get('https://horriblesubs.info/current-season/')
    page = BeautifulSoup(browser.page_source, features='html.parser')
    divs = page.body.find_all('div', attrs={'class': 'ind-show'})
    season = defaultdict(list)

    print('\nEnqueuing {0} shows'.format(len(divs)))

    try:
        for i, div in enumerate(divs):
            browser.get('https://horriblesubs.info{}'.format(div.a['href']))
            print('Enqueuing {}'.format(div.a.text))

            # Expand the whole listing to get all the episodes
            try:
                # Briefly wait to dodge `selenium.common.exceptions.ElementNotInteractableException`
                WebDriverWait(browser, 15)\
                    .until(EC.element_to_be_clickable((By.CLASS_NAME, 'more-button')))

                while True:
                    browser.find_element_by_class_name('more-button').click()
            except NoSuchElementException:
                pass

            page = BeautifulSoup(browser.page_source, features='html.parser')
            # Everything from here on should use BeautifulSoup, since the browser has done all it needs to
            # NOTE: When handling batches, this logic could stop when it hits the most recent episode

            if page.find('div', attrs={'class': 'batch-container'})['style'] == 'display: none;':
                episodes = page.body\
                    .find('div', attrs={'class': 'hs-shows'})\
                    .find_all('div', attrs={'class': 'rls-info-container'})

                for episode in episodes:
                    magnet = get_magnet(episode.find_all(
                        'div', attrs={'class': 'rls-link'})[::-1][0])
                    season[div.a.text].insert(0, magnet)
            else:
                batches = page.body\
                    .find('div', attrs={'class': 'hs-batches'})\
                    .find_all('div', attrs={'class': 'rls-info-container'})

                for batch in batches:
                    magnet = get_magnet(batch.find_all(
                        'div', attrs={'class': 'rls-link'})[::-1][0])
                    season[div.a.text].insert(0, magnet)

                most_recent_episode = batches[0].strong.string.split('-')[1]
                episodes = page.body\
                    .find('div', attrs={'class': 'hs-shows'})\
                    .find_all('div', attrs={'class': 'rls-info-container'})

                for episode in episodes:
                    if episode.strong.string == most_recent_episode:
                        break

                    magnet = get_magnet(episode.find_all(
                        'div', attrs={'class': 'rls-link'})[::-1][0])
                    season[div.a.text].insert(0, magnet)
    finally:
        browser.quit()

    try:
        # Web UI -> 'Bypass authentication for hosts on localhost' should be enabled
        # Downloads -> 'Do not start download automatically' should be enabled
        qb = Client('http://127.0.0.1:8080/')

        # Use DP to decrease show fetch time
        for path, magnets in season.items():
            for magnet in magnets:
                qb.download_from_link(magnet, savepath='{}{}'.format(
                    get_dl_path(), path), category='anime')

        qb.resume_all()
    except ConnectionError:
        print('[!] qBittorrent not active!')
