"""Product registry — GA4 / billing / Langfuse IDs (see docs/ui-setup-load-paths.md)."""

from __future__ import annotations

from dataclasses import dataclass

from insights.domain.models import Product


@dataclass(frozen=True)
class ProductSources:
    """Warehouse / Console IDs for one Digest product (all lenses)."""

    product: Product
    display_name: str
    # GA4
    ga4_property_id: str
    ga4_measurement_id: str
    ga4_dataset: str  # analytics_<property_id> after BigQuery Link
    # BQ location of the GA4 Link dataset (may differ from hub marts EU)
    ga4_location: str
    # GCP / Billing
    gcp_project_id: str
    billing_account_id: str
    # Langfuse (EU cloud)
    langfuse_project_name: str | None
    langfuse_project_id: str | None
    langfuse_org: str | None
    # UX — Contentsquare (KIH) or Clarity (Lindle/YCA). Only one primary per product.
    ux_primary: str  # "contentsquare" | "clarity"
    contentsquare_id: str | None
    clarity_project_id: str | None
    hotjar_id: str | None = None


BQ_HUB_PROJECT = "cognispace"
BQ_HUB_LOCATION = "EU"
LANGFUSE_HOST_DEFAULT = "https://cloud.langfuse.com"

PRODUCT_SOURCES: dict[Product, ProductSources] = {
    Product.KIH: ProductSources(
        product=Product.KIH,
        display_name="Dr Kiwi / Keep It Healthy",
        ga4_property_id="499549002",
        ga4_measurement_id="G-CBTHK8QQ6N",
        ga4_dataset="analytics_499549002",
        ga4_location="EU",  # Link landed in multi-region EU
        gcp_project_id="dr-kiwi-app",
        billing_account_id="01BF64-6A600F-517AFE",
        langfuse_project_name="DrKiwi",
        langfuse_project_id="cmph5si3406aoad0e8o2j8p4d",
        langfuse_org="Keep It Healthy (cmph5sdsp06ajad0e9vldfnn7)",
        ux_primary="contentsquare",
        contentsquare_id="57dec74d2513b",
        clarity_project_id=None,
    ),
    Product.LINDLE: ProductSources(
        product=Product.LINDLE,
        display_name="Lindle",
        ga4_property_id="506154105",
        ga4_measurement_id="G-71BSGEPP21",
        ga4_dataset="analytics_506154105",
        ga4_location="europe-central2",
        gcp_project_id="cognispace",
        billing_account_id="01C7B7-5B77CD-27EDAD",
        langfuse_project_name="Lindle",
        langfuse_project_id="cmei38jmn00s1ad07oqzvyqcz",
        langfuse_org="Synthapse (cmehh1da7003nad07axuh0p6a)",
        ux_primary="clarity",
        contentsquare_id=None,
        clarity_project_id="tfa09ihgyu",
    ),
    Product.YCA: ProductSources(
        product=Product.YCA,
        display_name="YCA / CzatBudowlany",
        ga4_property_id="494547928",
        ga4_measurement_id="G-DZNYJF6HSB",
        ga4_dataset="analytics_494547928",
        ga4_location="europe-central2",
        gcp_project_id="adroit-router-462912-n6",
        billing_account_id="01F545-2E8963-C6EBE1",
        langfuse_project_name="yca-ca-mvp",
        langfuse_project_id=None,  # name known; set id in env if needed
        langfuse_org=None,
        ux_primary="clarity",
        contentsquare_id=None,
        clarity_project_id="t9jhgsv5zv",
        hotjar_id="6502269",
    ),
}


def get_sources(product: Product | str) -> ProductSources:
    return PRODUCT_SOURCES[Product(product)]


def billing_export_table_id(billing_account_id: str) -> str:
    return "gcp_billing_export_resource_v1_" + billing_account_id.replace("-", "_")
