import requests
import re
import pandas as pd
import sys
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time
import json, os
import csv


def login(driver):
    signin_url = 'https://brazos.tx.publicsearch.us/signin'
    email = 'smartperson33@gmail.com'
    password = '112233445566??'
    driver.get(signin_url)
    driver.find_element_by_css_selector('#email').send_keys(email)
    driver.find_element_by_css_selector('.password-input__input--mask').send_keys(password)
    driver.find_element_by_css_selector('.user-form__button').click()


def scroll_shim(passed_in_driver, object):
    x = object.location['x']
    y = object.location['y']
    scroll_by_coord = 'window.scrollTo(%s,%s);' % (
        x,
        y
    )
    scroll_nav_out_of_way = 'window.scrollBy(0, -120);'
    passed_in_driver.execute_script(scroll_by_coord)
    passed_in_driver.execute_script(scroll_nav_out_of_way)


def remove_special_char(s):
    z = s.replace(' ', '-')
    z = z.replace('/', '-')
    removeSpecialChars = re.sub("[!@#$%^&*()[]{};:,./<>?\|`~=_+]", "-", z)
    return removeSpecialChars


def crawl_data(driver, url, issue_record, issue_url):
    try:
        url = url + '&viewType=list'
        driver.get(url)
        offset = 0
        print('CRAWLING .......', url)
        data_dic = {}
        while True:
            if driver.find_elements_by_xpath('//h3[@class="no-search-results__header-title"]'):
                return {}
            else:
                WebDriverWait(driver, 45).until(EC.visibility_of_element_located(
                    (By.XPATH, '//div[@class="search-results__results-wrap"]/div/table/tfoot')))
                actionChains = ActionChains(driver)
                trs = driver.find_elements_by_xpath('//tr')[2:]
                for tr in trs:
                    item_dic = {
                        'OR': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-3"]').text),
                        'EE': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-4"]').text),
                        'DT': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-5"]').text),
                        'DATE': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-6"]').text),
                        'DN': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-7"]').text),
                        'BVP': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-8"]').text),
                        'LD': remove_special_char(tr.find_element_by_xpath('.//td[@class="col-9"]').text),
                    }

                    key = item_dic['DN'].split('-')[1]
                    # print(item_dic)

                    data_dic[key] = item_dic
                # print(data_dic)
                card_view_url = driver.current_url.replace('&viewType=list', '&viewType=card')
                # print(card_view_url)
                driver.get(card_view_url)
                WebDriverWait(driver, 50).until(EC.visibility_of_element_located(
                    (By.XPATH, '//div[@class="result-card"]')))

                image_dic = {}
                cards = driver.find_elements_by_xpath('//div[@class="result-card"]')

                for c in cards:

                    scroll_shim(driver, c)
                    no_pages = int(
                        c.find_element_by_xpath('.//div/p[text()="Number of Pages"]/following-sibling::*').text)
                    doc_no = c.find_element_by_xpath('.//div/p[text()="Document Number"]/following-sibling::*').text
                    thumbnail_url = WebDriverWait(c, 45).until(EC.visibility_of_element_located(
                        (By.XPATH, './/*[@class="thumbnail__image"]'))).get_attribute('src')

                    img_urls = [thumbnail_url.replace('1_r-300', str(i)) for i in range(1, no_pages + 1)]
                    doc_no = doc_no.split('-')[1]
                    if data_dic.get(doc_no):
                        data_dic[doc_no]['img_urls'] = img_urls
                    else:
                        issue_record.write(str(doc_no + ',\n'))
                if driver.find_elements_by_xpath('//button[@aria-label="next page" and @aria-disabled="false"]'):
                    offset += 250
                    next_url = url + '&offset={}'.format(offset)
                    driver.get(next_url)
                    print('CRAWLING .......', next_url)
                    continue
                return data_dic
    except:
        issue_url.write(str(driver.current_url + '\n'))
        return {}


def download_pdf(driver, data, dir_path):
    print('downloading data -------------')
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
    }
    req_session = requests.session()
    req_session.headers.update(headers)

    for cookie in driver.get_cookies():
        c = {cookie['name']: cookie['value']}
        req_session.cookies.update(c)

    for _, d in data.items():
        pdf_file_name = '/BVP-{}--DN-{}--DT-{}--LD-{}--EE-{}--OR{}.pdf'.format(d['BVP'], d['DN'], d['DT'], d['LD'],
                                                                               d['EE'], d['OR'])
        file_path = dir_path + pdf_file_name
        img_list = [Image.open(req_session.get(img, stream=True).raw).convert('RGB') for img in d['img_urls']]
        img_list[0].save(file_path, save_all=True, append_images=img_list[1:])


if __name__ == '__main__':
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--incognito')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
    # dir_path = '/content/drive/MyDrive/Brazos-Research'
    dir_path = os.getcwd()
    csv_file = dir_path + '/data3.csv'
    csv_columns = ['OR', 'EE', 'DT', 'DATE', 'DN', 'BVP', 'LD', 'img_urls']
    writer = open(dir_path + '/crawled_url.txt', 'a+')
    write_data = open(dir_path + '/crawled_data.txt', 'a+')
    issue_record = open(dir_path + '/issue_in_record.txt', 'a+')
    issue_url = open(dir_path + '/issue_in_url.txt', 'a+')
    data = pd.read_excel('input.xlsx', sheet_name='Sheet2').fillna("")
    urls = list(data.URL)
    urls.reverse()
    login(driver)
    urls_file = open('crawled_urls.txt', 'a+')

    with open(csv_file, 'a+') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        count = 0
        for url in urls[127:]:
            if url:
                count += 1
                print(count)
                data_dic = crawl_data(driver, url, issue_record, issue_url)
                # writer.write(str(url+', \n'))
                for _, data in data_dic.items():
                    writer.writerow(data)
            # write_data.write(json.dumps(data_dic))
            # download_pdf(driver,data_dic, dir_path)
            time.sleep(1)