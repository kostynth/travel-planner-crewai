from icrawler.builtin import BingImageCrawler

crawler = BingImageCrawler(
    storage={"root_dir": "data/images"},
    feeder_threads=1,
    parser_threads=1,
    downloader_threads=4,
)
crawler.crawl(
    keyword="杭州西湖",
    max_num=20,
)