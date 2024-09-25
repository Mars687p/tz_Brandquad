import time
from typing import Generator

import scrapy
from fixprice.settings import (LOCALITY_COOCKIES, PROXY, PROXY_PASSWORD,
                               PROXY_USER)
from fixprice.types import (AssetsProduct, PriceData, ProductDetail,
                            StockProduct)
from scrapy.http import Request, Response
from scrapy_playwright.page import PageMethod


class CatalogFixPriceSpider(scrapy.Spider):
    name = "catalog_fixprice"
    user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

    cookie_dict = {'locality': LOCALITY_COOCKIES
                   }
    if PROXY:
        custom_settings = {
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "proxy": {
                    "server": PROXY,
                    "username": PROXY_USER,
                    "password": PROXY_PASSWORD,
                },
            }
        }

    def start_requests(self) -> Generator[Request, None, None]:
        urls = [
            "https://fix-price.com/catalog/kosmetika-i-gigiena?page=1",
        ]
        for url in urls:
            yield scrapy.Request(url=url, cookies=self.cookie_dict, callback=self.parse)

    def parse(self, response: Response) -> Generator[Request, None, None]:
        list_link_product: list[str] = []
        for i, product in enumerate(
                        response.css('div.category-content').css('div.products')
                        .css('div.product__wrapper').css('div.details').css('div.description')):
            list_link_product.append(product.css('a::attr(href)').get())
            if i > 5:
                break

        for link in list_link_product:
            if PROXY:
                yield response.follow(
                    link,
                    callback=self.get_detail_product,
                    cookies=self.cookie_dict,
                    meta={
                        'download_timeout': 15,
                        'playwright': True,
                        'playwright_include_page': True,
                        'playwright_context_kwargs': {
                                "ignore_https_errors": True,
                        },
                        'playwright_page_methods': [PageMethod(
                                            'wait_for_selector', 'div.page-content',
                                            timeout=10000)]
                    })
            else:
                yield response.follow(
                    link,
                    callback=self.get_detail_product,
                    cookies=self.cookie_dict,
                    meta={
                        'download_timeout': 15,
                        'playwright': True,
                        'playwright_include_page': True,
                        'playwright_page_methods': [PageMethod(
                                            'wait_for_selector', 'div.page-content')]
                    })

        page = response.xpath('//div[@class="pagination pagination"]').get()
        if page is not None:
            n_page = int(response.url.split('?page=')[1]) + 1
            print(f'{n_page=}')
            yield response.follow(
                    f'https://fix-price.com/catalog/kosmetika-i-gigiena?page={n_page}',
                    self.parse)

    def get_detail_product(self, response: Response) -> Generator[ProductDetail, None, None]:
        div_product = response.css('div.product')
        detail = div_product.css('div.product-details')
        div_image = div_product.css('div.product-images')

        properties: dict[str, str] = {}
        for item in detail.css('div.properties').css('p.property'):
            key = item.css('span.title::text').get()
            if key == 'Бренд':
                properties[key] = item.css('a::text').get(default='')
                continue
            properties[key] = item.css('span.value::text').get(default='')

        marketing_tags: list[str] = []
        for item in div_image:
            marketing_tags.append(item.xpath(
                            '//div[@class="big isSpecialPrice"]/text()').get(default=''))

        sections: list[str] = []
        for section in response.css('div.header').css('div.crumb'):
            sections.append(section.css('span::text').get(default=''))

        price_block = detail.css('div.visible-part')
        regular_price = self.get_price_in_float(price_block.css('div.regular-price::text').get())
        special_price = price_block.css('div.special-price').get(default=regular_price)
        price = PriceData({
                "current": (special_price if type(special_price) is float
                            else self.get_price_in_float(special_price)),
                "original": regular_price,
                "sale_tag": f"Скидка {int(100-(regular_price/special_price*100))}%"
                })

        # Count можно получить из запроса cart после добавления продукта
        # но для определенного магазина, поэтому не добавлял
        # is_stock = detail.css('div.product-stock::text').get() == 'В наличии'
        stock = StockProduct({
            'in_stock': True,
            'count': 1
            })

        assets = AssetsProduct({
                "main_image": "",
                "set_images": [],
                "view360": [],
                "video": []
        })

        for index, img in enumerate(div_image.xpath(
                        '//div[@class="slider gallery"]').css('link::attr(href)')):
            if index == 0:
                assets['main_image'] = img.get()
            assets['set_images'].append(img.get())

        product_detail = ProductDetail({
            "timestamp": int(time.time()),
            "RPC":  properties.get('Код товара', ''),
            "url": response.url,
            "title": response.css('h1.title::text').get(),
            "marketing_tags": marketing_tags,
            "brand": properties.get('Бренд', ''),
            "section": sections[:len(sections)-1],
            "price_data": price,
            "stock": stock,
            "assets": assets,
            "metadata": properties,
            "variants": 1,
        })

        yield product_detail

    def get_price_in_float(self, string: str) -> float:
        return float(string.split(' ')[0])
