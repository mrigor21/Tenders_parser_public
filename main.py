'''
Это мой первый хоть сколько-нибудь серьезный скрипт. Написан во второй половине
2021 года когда я еще даже не был разработчиком. С него начался мой
поиск работы в должности разработчика.

Скрипт был написан для строительной компании в сфере электроэнергетики для
автоматического поиска подходящих конкурсов на строительство на крупных
торговых площадках: РОСЭЛТОРГ и ПОЛЮС. Поиск происходит по ключевым словам
без использования регулярных выражений. Отобранные конкурсы каждый день отправляются в
почтовые ящики директора и руководителя проектов и сохраняются в файл.
В следующий раз при нахождении этого же конкурса, скрипт увидит, что
он уже был обработан и сообщение на почту высылать не будет повторно.

Код компилировался в exe файл и ставился на автозагрузку компьютера
руководителя проектов, работал каждое утро, когда он приходил на работу.
Планировалось расширение этого алгоритма, добавление других площадок,
хост на сервере. Руководству это в какой-то момент перестало быть нужно,
и я уволился, потому что работа инженером ПТО была скучной =(
Теперь я пишу программы для инженеров ПТО =)
'''


from bs4 import BeautifulSoup
from urllib.request import urlopen
import lxml
import os
import pandas as pd
import smtplib
from email.message import EmailMessage
import datetime
pd.options.mode.chained_assignment = None


class Screener:
    def __init__(self):
        self.roseltorg_url_opened = [
                        # ОКПД2 - D, ОКПД2 - F, ОКПД2 - M по РФ от 13 млн. рублей
                        'https://www.roseltorg.ru/procedures/search?sale=1&status%5B%5D=0&okpd2%5B%5D=D&okpd2%5B%5D=F&okpd2%5B%5D=M&start_price=12+999+999&currency=all',
                        # Поиск по Алтайскому краю, Свердловской, Челябинской, Томской, Кемеровской и Новосибирской областям до 13 млн
                        'https://www.roseltorg.ru/procedures/search?sale=1&status%5B%5D=0&region%5B%5D=22&region%5B%5D=42&region%5B%5D=54&region%5B%5D=66&region%5B%5D=70&region%5B%5D=74&end_price=13+000+001&currency=all'
                        ]
        self.roseltorg_url_closed = [# ОКПД2 - D, ОКПД2 - F, ОКПД2 - M-71 по РФ от 13 млн. рублей
                                     'https://www.roseltorg.ru/procedures/search?sale=1&status%5B%5D=4&okpd2%5B%5D=D&okpd2%5B%5D=F&okpd2%5B%5D=71&start_price=12+999+999&currency=all&start_date_published=',
                                     # Поиск по Алтайскому краю, Свердловской, Челябинской, Томской, Кемеровской и Новосибирской областям до 13 млн
                                     'https://www.roseltorg.ru/procedures/search?sale=1&status%5B%5D=4&region%5B%5D=22&region%5B%5D=42&region%5B%5D=54&region%5B%5D=66&region%5B%5D=70&region%5B%5D=74&end_price=13+000+001&currency=all&start_date_published='
                                     ]
        start_date = str((pd.to_datetime(datetime.date.today(), dayfirst=True) - pd.Timedelta('30 day')).strftime('%d-%m-%Y %X'))[:10].replace('-', '.')
        start_date = start_date[:6] + start_date[8:]
        for i in range(2):
            self.roseltorg_url_closed[i] += start_date
        self.polus_url_opened = ['https://tenders.polyus.com/purchases/?PT=26382']
        self.path = '/content/drive/MyDrive/Competition screener/Полюс + Росэлторг' # Указать путь расположения программы
        self.email = 'some_email@gmail.com'
        self.password = 'some_password'
        self.roseltorg_base_url = 'https://www.roseltorg.ru'
        self.roseltorg_base_search_url = 'https://www.roseltorg.ru/procedures/search'
        self.polus_base_url = 'https://tenders.polyus.com/purchases/'
        self.procedure_urls = []
        self.old_competitions = pd.read_csv(os.path.join(self.path, 'old_competitions.csv'), index_col=0)['0']
        self.name_keywords = [
            'шкаф', 'ШКАФ', 'Шкаф',
            'СГП', 'ит собственных нужд', 'ЩСН', 'ульт управления',
            'ащита линии', 'ащиты линии', 'ащита линий', 'ащиты линий',
            'РЗА', 'РЗиА', 'ЗДЗ', 'ЦС', 'ОБР', 'СОИ', 'АЧР',
            'ДГР', 'БИМ', 'РАС', 'АВР',
            'АИИС КУЭ', 'АИИСКУЭ', 'РУ', 'КТПН',
            'ифференциальной защиты', 'СОПТ', 'релейной защиты', 'САОН',
            'оперативной блокировки', 'центральной сигнализации',
            'УСПД', 'дуговой защиты',
            'ШКТИ', 'ШЗТ', "ШКТИ", "УСПД", "РПН", "ЩЦС", "ШЗВ", "ШУ", "ШС",
            'ЯЗВ', 'ОБР', "АСКУЭ",
            'анель управления', 'анели управления',
            'АКБ', 'щиток связи', "щитка связи", "щитков связи",
            'ит учета', 'ита учета', 'итов учета'
        ]
        self.name_antikeywords = [
            'ЦТП', 'просек', 'асчистк', 'двер', 'канализаци',
            'водоснабжени', 'теплоснабжени', 'водопровод',
            'отоплени', 'ограждени', 'водоотведени', 'ИТП',
            'водовод', 'ИВЛ'
        ]
        self.send_errors = False
        self.months = ['Янв', 'Фев', 'Мар', 'Апр',
                       'Май', 'Июн', 'Июл', 'Авг',
                       'Сен', 'Окт', 'Ноя', 'Дек']
        self.scan_new_tenders = True

    def get_search_info(self):
        search_info = open(os.path.join(self.path, 'search_info.txt'), 'r').read()
        lines = search_info.split('\n')
        lines = list(filter(None, lines))
        for line in lines:
            if 'New tenders receivers' in line:
                receiver = line[line.find(':') + 1:]
                self.receiver_new = [x.strip() for x in receiver.split(',')]
            if 'Ended tenders receivers' in line:
                receiver = line[line.find(':') + 1:]
                self.receiver_old = [x.strip() for x in receiver.split(',')]
            if 'Send errors' in line:
                send_errors = line[line.find(':') + 1:].strip()
                self.send_errors = bool(send_errors)

    def get_pages_polus(self, url):
        self.url_pages = []
        html = urlopen(url).read().decode("utf-8")
        soup1 = BeautifulSoup(html, 'lxml')
        pagination = soup1.find('div', class_='page_nav')
        if pagination is None:
            self.url_pages.append(url)
        else:
            last_page = pagination.find_all('a', class_=['page larger active', 'page larger', 'page larger '])[-1].text
            for i in range(int(last_page)):
                self.url_pages.append(f'{url}?&PAGEN_1={i+1}')
    
    def get_pages_roseltorg(self, url):
        html = urlopen(url).read().decode("utf-8")
        soup1 = BeautifulSoup(html, 'lxml')
        pagination = soup1.find('nav', class_='pagination')
        page_numbers = []
        self.url_pages = []
        if pagination is None:
            self.url_pages.append(url)
        else:
            ellipsis_flag = True
            ellipsis_flag_new = True
            first_while = True
            while ellipsis_flag_new:
                ellipsis_flag_new = ellipsis_flag
                for index1, page in enumerate(pagination.find_all('a', class_='pagination__link')):
                    str_page_href = str(page['href'])
                    ind = str_page_href.find('page')
                    try:
                        page_number = int(str_page_href[ind + 5:ind + 8])
                    except:
                        try:
                            page_number = int(str_page_href[ind + 5:ind + 7])
                        except:
                            page_number = int(str_page_href[ind + 5:ind + 6])
                    if first_while:
                        page_url = self.roseltorg_base_search_url + page['href'] + f'&from={len(self.url_pages) * 10}'
                        first_while = False
                    else:
                        ind = page['href'].find('from')
                        page['href'][:ind - 1]
                        page_url = self.roseltorg_base_search_url + page['href'][
                                                          :ind - 1] + f'&from={len(self.url_pages) * 10}' + f'&page={page_number}'
                    if page_number not in page_numbers:
                        self.url_pages.append(page_url)
                        page_numbers.append(page_number)
                middle_page = BeautifulSoup(urlopen(self.url_pages[-2]).read().decode("utf-8"), 'lxml')
                pagination = middle_page.find('nav', class_='pagination')
                str_pagination = str(pagination)
                second_half_pagination = BeautifulSoup(str_pagination[int(len(str_pagination) / 2):], 'lxml')
                ellipsis = second_half_pagination.find('span', class_='pagination__separator')
                if ellipsis is not None:
                    ellipsis_flag = True
                else:
                    ellipsis_flag = False

    def find_procedures_polus(self):
        i=0
        for index1, page_url in enumerate(self.url_pages):
            html = urlopen(page_url).read().decode("utf-8")
            soup2 = BeautifulSoup(html, 'lxml')
            page_results = soup2.find('tbody').find_all('tr')
            for index2, res in enumerate(page_results):
                try:
                    published, end_time = res.find_all('p', class_='date')
                    published = published.text.strip()
                    published = f'{published[:len(published)-3]} {published[-3:]}'
                    end_time = end_time.text.strip().replace(' ', '')
                    for m in self.months:
                        if m in end_time:
                            end_time = end_time.replace(m, f'.{self.months.index(m)+1}.')
                    name = res.find('a', class_='no-underline').text
                    proc_url = self.polus_base_url + res.find('a', class_='no-underline')['href']
                    customer = res.find('div', class_='filter_types_link').a.text.replace('\t', '').replace('\n','')
                    condition = (proc_url not in self.old_competitions.values) and \
                                (pd.to_datetime(datetime.datetime.now()) < pd.to_datetime(end_time, dayfirst=True)) and \
                                ((any(name.find(keyword) >= 0 for keyword in self.name_keywords)) and \
                                (not any(name.find(antikeyword) >= 0 for antikeyword in self.name_antikeywords)))
                    if condition:
                        i += 1
                        print(f'Совпадение № {i}')
                        msg = EmailMessage()
                        msg['From'] = self.email
                        msg['To'] = self.receiver_new
                        msg['Subject'] = 'Новый конкурс на "ПОЛЮС" (прием заявок)'
                        content = f'''Наименование: {name}
Организатор: {customer}
Дата публикации: {published}
Окончание приема заявок: {end_time}
Ссылка на процедуру: {proc_url}'''
                        msg.set_content(content)
                        print(content)
                        print('______________________________________________')
                        print('')
                    self.procedure_urls.append(proc_url)
                except Exception as e:
                    if self.send_errors:
                        msg = EmailMessage()
                        msg['Subject'] = 'Ошибка в программе по поиску конкурсов на "ПОЛЮС"'
                        msg['From'] = self.email
                        msg['To'] = 'some_email@gmail.com'
                        content = f'''Error type: {type(e)}
Error message: {str(e)}
Error occurred while scanning the result № {index2 + 1} on page № {index1 + 1}
Page URL: {page_url}
Procedure URL: {proc_url}'''
                        msg.set_content(content)
                        print(content)
                        print('______________________________________________')
                        print('')

    def find_procedures_roseltorg(self):
        i=0
        for index1, page_url in enumerate(self.url_pages):
            html = urlopen(page_url).read().decode("utf-8")
            soup2 = BeautifulSoup(html, 'lxml')
            page_results = soup2.find_all('div', class_='search-results__item')
            for index2, res in enumerate(page_results):
                try:
                    procedure, name = res.find_all('a', class_='search-results__link')
                    proc_url = self.roseltorg_base_url + procedure['href']
                    if '\n' in str(name.text):
                        name = name.text[:str(name.text).find('\n')]
                    else:
                        name = name.text
                    section = res.find('p', class_='search-results__tooltip', title='Торговая секция').text
                    customer = res.find('p', class_='search-results__tooltip', title=['Продавец', 'Организатор']).text
                    region = res.find('p', class_='search-results__tooltip', title='Регион заказчика')
                    procedure_type = res.find('p', class_='search-results__type').text
                    sum = res.find('div', class_='search-results__sum').p.text
                    end_time_tag = res.find('div', class_='search-results__infoblock search-results__finish-time')
                    end_time = str(end_time_tag.time.text).split('\n')[0]
                    span = end_time_tag.time.span.text
                    if self.scan_new_tenders:
                        condition = (proc_url not in self.old_competitions.values) and \
                                    (pd.to_datetime(datetime.datetime.now()) < pd.to_datetime(end_time.replace(' в', ''),
                                                                                              dayfirst=True)) and \
                                    ((any(name.find(keyword) >= 0 for keyword in self.name_keywords)) and \
                                    (not any(name.find(antikeyword) >= 0 for antikeyword in self.name_antikeywords)))
                    else:
                        condition = (proc_url not in self.old_competitions.values) and \
                                    ((any(name.find(keyword) >= 0 for keyword in self.name_keywords)) and \
                                    (not any(name.find(antikeyword) >= 0 for antikeyword in self.name_antikeywords)))
                    if condition:
                        i+=1
                        print(f'Совпадение № {i}')
                        msg = EmailMessage()
                        msg['From'] = self.email
                        if self.scan_new_tenders:
                            msg['To'] = self.receiver_new
                            msg['Subject'] = 'Новый конкурс на "РОСЭЛТОРГ" (прием заявок)'
                        else:
                            msg['To'] = self.receiver_old
                            msg['Subject'] = 'Завершенный конкурс на "РОСЭЛТОРГ"'
                        content = f'''Процедура: {procedure.text}
Наименование: {name}
Тип процедуры: {procedure_type}
Торговая секция: {section}
Организатор: {customer}
Сумма: {sum} ₽
Окончание приема заявок: {end_time} {span}
Ссылка на процедуру: {proc_url}'''
                        try:
                            content += f"\nРегион заказчика: {region.text}"
                        except:
                            content += f"\nРегион заказчика: не указан"
                        msg.set_content(content)
                        print(content)
                        print('______________________________________________')
                        print('')
                    self.procedure_urls.append(proc_url) # Приклеиваем к просмотренным конкурсам, только если выполнили
                    # всю обработку, иначе надо вернуться к этому конкурсу повторно при следующем запуске
                except Exception as e:
                    if self.send_errors:
                        msg = EmailMessage()
                        msg['Subject'] = 'Ошибка в программе по поиску конкурсов на "РОСЭЛТОРГ"'
                        msg['From'] = self.email
                        msg['To'] = 'some_email@gmail.com'
                        content = f'''Error type: {type(e)}
Error message: {str(e)}
Error occurred while scanning the result № {index2 + 1} on page № {index1 + 1}
Page URL: {page_url}
Procedure URL: {proc_url}'''
                        msg.set_content(content)
                        print(content)
                        print('______________________________________________')
                        print('')

    def run(self):
        self.get_search_info()
        for url in self.roseltorg_url_opened:
            self.get_pages_roseltorg(url)
            print(self.url_pages[-1])
            self.find_procedures_roseltorg()
            print('________________________________________________________________________')
            print('________________________________________________________________________')
            print('')
        for url in self.polus_url_opened:
            self.get_pages_polus(url)
            print(self.url_pages[-1])
            self.find_procedures_polus()
            print('________________________________________________________________________')
            print('________________________________________________________________________')
            print('')
        self.scan_new_tenders = False
        for url in self.roseltorg_url_closed:
            self.get_pages_roseltorg(url)
            print(self.url_pages[-1])
            self.find_procedures_roseltorg()
            print('________________________________________________________________________')
            print('________________________________________________________________________')
            print('')
        pd.Series(self.procedure_urls).to_csv(os.path.join(self.path, 'old_competitions.csv'))


S = Screener()
old_competitions = pd.read_csv(os.path.join(S.path, 'old_competitions.csv'), index_col=0)['0']
S.run()



