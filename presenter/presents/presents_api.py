import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from conf import configuration as config

import logging
log = logging.getLogger(__name__)

from amazonproduct import API
amz_api = API(access_key_id=config.AMZ_ACCESS_KEY, secret_access_key=config.AMZ_SECRET_KEY, associate_tag=config.AMZ_ASSOCIATE_TAG, locale='us')

from ebaysdk.shopping import Connection as Shopping
from ebaysdk.exception import ConnectionError

import locale
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()


def get_amz_items(args):
    items = []
    try:
        for index, result in enumerate(amz_api.item_search('All', Keywords=args["keywords"], Availability='Available', Condition='New')):
            if (index == config.MAX_NUMBER_OF_RESULTS):
                break
            item = {}
            try:
                detailed_item_info = amz_api.item_lookup(result.ASIN.text, Condition='New', ResponseGroup='Large')
                item["title"] = result.ItemAttributes.Title.text
                item["link"] = result.ItemLinks.ItemLink.URL.text
                item["price"] = get_item_price_amz(detailed_item_info)
                item["image"] = get_item_image_amz(detailed_item_info, 'Large')
                item["type"] = get_item_type_amz(detailed_item_info)
                item["source"] = "amazon"
                items.append(item)
            except Exception:
                log.exception("failed get info for result %s" % str(result))
                continue
    except Exception:
        log.exception("error request in the amazon api")

    return items


def get_ebay_items(args):
    ebay_api = Shopping(domain=config.EBAY_DOMAIN_PROD, debug=False, appid=config.EBAY_APP_ID_PROD, config_file=None, warnings=True)

    try:
        response = ebay_api.execute('FindPopularItems', {'QueryKeywords': args["keywords"]})

        items = []
        for result in response.reply.ItemArray.Item:
            item = {}
            item["title"] = result.Title
            item["link"] = result.ViewItemURLForNaturalSearch
            item["price"] = locale.currency(float(result.ConvertedCurrentPrice.value), grouping=True)
            item["image"] = "http://thumbs3.ebaystatic.com/d/l225/pict/" + result.ItemID + "_1.jpg"
            item["type"] = result.PrimaryCategoryName
            item["source"] = "ebay"
            items.append(item)

    except ConnectionError:
        log.exception("failed connect to ebay api")

    return items


def get_presents(args):
    args = validate_args(args)
    cache_key = get_cache_key(args)
    log.info("cache key is: %s ; args: %s" % (cache_key, args))

    cache_result = cache.get(cache_key)
    if cache_result:
        cache_result[1]["cache"] = True
        return cache_result

    meta = {}
    all_items = []
    items_from_amz = get_amz_items(args)
    items_from_ebay = get_ebay_items(args)

    all_items.extend(items_from_amz)
    all_items.extend(items_from_ebay)

    meta["cache"] = False
    meta["number_of_items"] = len(all_items)
    meta["number_of_items_amazon"] = len(items_from_amz)
    meta["number_of_items_ebay"] = len(items_from_ebay)
    all_items.sort(key=lambda x: float(x["price"].replace("$", "").replace("Not Available", "99999999999")))

    cache.set(cache_key, (all_items, meta), timeout=config.CACHE_TIMEOUT_MINUTES * 60)
    return all_items, meta


def get_item_price_amz(item):
    """
    Get Offer Price and Currency.
    Return price according to the following process:
    * If product has a sale, return Sales Price, otherwise,
    * Return Price, otherwise,
    * Return lowest offer price, otherwise,
    * Return None.
    :return:
        A tuple containing:
            1. Float representation of price.
            2. ISO Currency code (string).
    """

    try:
        price = item.Items.Item.Offers.Offer.OfferListing.SalePrice.FormattedPrice.text
    except:
        try:
            price = item.Items.Item.Offers.Offer.OfferListing.Price.FormattedPrice.text
        except:
            try:
                price = item.Items.Item.OfferSummary.LowestNewPrice.FormattedPrice.text
            except:
                price = "Not Available"

    return price


def get_item_image_amz(item, size):
    try:
        if size.lower() == "small":
            return item.Items.Item.SmallImage.URL.text
        elif size.lower() == "medium":
            return item.Items.Item.MediumImage.URL.text
        else:
            return item.Items.Item.LargeImage.URL.text
    except:
        return "Not Available"


def get_item_type_amz(item):
    try:
        return item.Items.Item.ItemAttributes.Binding.text
    except:
        return "Not Available"


def validate_args(args):
    args = dict(args)

    keywords = args.get("keywords")
    if keywords:
        args["keywords"] = keywords

    min_price = args.get("min_price")
    if min_price:
        args["min_price"] = min_price

    max_price = args.get("max_price")
    if max_price:
        args["max_price"] = max_price

    return args


def get_cache_key(args):
    return hash(tuple(args.items()))


if __name__ == '__main__':
    print get_presents({"keywords": "iphone"})
