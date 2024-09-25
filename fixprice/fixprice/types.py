from typing import TypedDict


class PriceData(TypedDict):
    current: float
    original: float
    sale_tag: str


class StockProduct(TypedDict):
    in_stock: bool
    count: int


class AssetsProduct(TypedDict):
    main_image: str
    set_images: list[str]
    view360: list[str]
    video: list[str]


class ProductDetail(TypedDict):
    timestamp: int
    RPC: str
    url: str
    title: str
    marketing_tags: list[str]
    brand: str
    section: list[str]
    price_data: PriceData
    stock: StockProduct
    assets: AssetsProduct
    metadata: dict  # type: ignore
    variants: int
